---
title: "Thinking about templating, part 2: Handling missing data"
layout: post
highlighter: rouge
tags: freeipa
---

## Contents
{:.no_toc}
* TOC
{:toc}

## Introduction
This post is a followup to
[Thinking about templating for automatic CSR generation]({% post_url 2016-07-19-csr-generation-templating %}).
In it we will look at a requirement of the templating system that was not
discussed in that post, and see how it is handled by the implementation.

Sometimes you might want to generate a certificate for a principal that doesn't
have all the fields referenced in the profile. This could be due to an error
(e.g.  used the "user" profile for a "service" principal) or just the way the
data is (e.g. the principal has no email address, or the requesting user has no
access to that field). We want to handle this cleanly by omitting the sections
of config that have missing data.

## Simple approach: data rules only
We can pretty simply update our data rules to do this partly right, like in this example:
{% highlight jinja %}
{% raw %}
{% if subject.fqdn.0 %}DNS = {{subject.fqdn.0}}{% endif %}
{% endraw %}
{% endhighlight %}

This adds some extra work for administrators creating new rules, and is another
step that someone could forget, but could be manageble.

However, if *none* of the data rules for a field has any data, we need to avoid
rendering the syntax rule for that field as well, otherwise we get weird empty
sections that openssl doesn't like. Modifying the rule templates can't solve
this problem, because the syntax rule in the database intentionally doesn't
know what data it may depend on for different profiles; that all depends on the
data rules.

## Syntax rules: See if something renders
We can make it work by having syntax rules insert templating to compute the
data rules first, then render their text only if some syntax rule rendered.
In its raw form, this gets ugly (see [1] for explanation):

{% highlight jinja %}
{% raw %}
{% set extension = true %}{% raw %}{% set contents %}{%{% endraw %}{% raw %} endraw %}
{{ datarules|join('\n') }}{% raw %}{% endset %}{% if contents %}
{%{% endraw %}{% raw %} endraw %}subjectAltName = @{% call openssl.section() %}{% raw %}
{{ contents }}{%{% endraw %}{% raw %} endraw %}{% endcall %}{% raw %}{% endif %}{%{% endraw %}{% raw %} endraw %}
{% endraw %}
{% endhighlight %}

For comparison, that rule used to look like this:
{% highlight jinja %}
{% raw %}
{% set extension = true %}subjectAltName = @{% call openssl.section() %}
{{ datarules|join('\n') }}{% endcall %}
{% endraw %}
{% endhighlight %}

I think this might be a heavy burden for administrators who want to write new
syntax rules.

However, we can introduce some macros to make this better. One macro,
`datarule` updates a value in a dict to true when a rule renders.  Another,
`syntaxrule`, initially sets the value to false, renders its data rules into a
variable, then renders the result to the output only if the variable is
nonempty. We can apply a similar technique to the fields in the data rules,
rendering the rule only if all fields are present. If we do so, the framework
can automatically wrap all syntax rules in
`{% raw %}{% call ipa.syntaxrule() %}...{% endcall %}{% endraw %}` and all data
rules in `{% raw %}{% call ipa.datarule() %}...{% endcall %}{% endraw %}`, and
the only modifications necessary to the rules themselves are to wrap all field
references that could be empty for lack of data, in `ipa.datafield()`, for
example:
{% highlight jinja %}
{% raw %}
{{ ipa.datafield(subject.mail.0) }}
{% endraw %}
{% endhighlight %}

### Issues
This system seems to be working fairly well, but it has a few drawbacks.

The macros to do this are a little arcane, as can be seen in [2], and can't be
commented very well as any whitespace becomes part of the macro output.  They
rely on global variables within the template, but this should be ok as long as
we always nest datafields within datarules within syntaxrules, and never nest
more than once.

Syntax rules with multiple assigned data rules present a problem.  Generally we
will want the results of those rules to be presented in the output with some
character in between, e.g.
`{% raw %}{{datarules|join(',')}}{% endraw %}` for certutil. However, when we
finally render this template with data, what if one of our datarules renders
while another does not due to lack of data? The above rule segment would
produce a template like:

{% highlight jinja %}
{% raw %}
{% call ipa.datarule() %}email:{{ipa.datafield(subject.mail.0)|quote}}{% endcall %},{% call ipa.datarule() %}uri:{{ipa.datafield(subject.inetuserhttpurl.0)|quote}}{% endcall %}
{% endraw %}
{% endhighlight %}

If this subject has no `inetuserhttpurl` field, the second `ipa.datarule` will
be suppressed, leaving an empty string. But, the comma will still be there!
This creates odd-looking output like the following:
{% highlight bash %}
--extSAN email:,myuser@example.com,,
{% endhighlight %}

Fortunately, certutil seems not to mind these extra commas, and openssl is also
ok with the extra blank lines that arise the same way, so this isn't breaking
anything right now. But, it's worrying not to be able to do much to improve
this formatting.

Third, there is an unfortunate interaction between the macros created for this
technique, the above issue, and the macro that produces openssl sections. That
macro [3] also relies on side effects to do its job - the contents of the
section are appended to a global list of sections, while only the section name
is returned at the point where the macro is called. Since the technique
discussed in this section evaluates each data rule to see if it produces any
data, if the rule includes an openssl section, a section is stored on rule
evaluation even if it has no data. Again, openssl is ok with the extra sections
as long as they are not referenced within the config file, but the result is
ugly.

## Syntax rules: Declare data dependencies
Another approach to suppressing syntax rules when none of their data rules are
going to render is to take the "simple approach" of listing the required data
items in an `{% raw %}{% if %}{% endraw %}` statement one step further. We
could amend the schema for data rules to include a record of the included data
item, so that each rule would know its dependencies. Data rules could then be
automatically wrapped so they wouldn't be rendered if this item was
unavailable. Syntax rules could be treated similarly; by querying the
dependencies of all the data rules it was configured to include, the whole
syntax rule could be suppressed if none of those items were available.

In this scheme, the template produced would look like:
{% highlight jinja %}
{% raw %}
{% if subject.mail.0 or subject.inethttpurl.0 %}--extSAN {% if subject.mail.0 %}email:{{subject.mail.0|quote}}{% endif %},{% if subject.inethttpurl.0 %}uri:{{subject.inethttpurl.0|quote}}{% endif %}{% endif %}
{% endraw %}
{% endhighlight %}

This takes care of the third problem of the previous solution, because data
rules with missing data will never be evaluated, meaning that superfluous
openssl sections will not be added. However, the second problem still persists,
because the commas and newlines are part of the syntax rule (which is rendered)
not the data rules (some of which aren't rendered).

## Suppressing excess commas and newlines

## Rethinking "template interpolation"

## Conclusions
One way I can think of to get around this is (1) to have data rules declare in LDAP what data they use. Then the renderer can automatically generate `{% raw %}{% if %}{% endraw %}` statements around both the data rules and the syntax rules based on the availability of data referenced in the data rules. Then no manual modifications to the rules are necessary. Another option (2) is that it may be possible to use macros or jinja2 extensions to add some syntactic sugar for this situation, though I haven't figured out quite how to do that nicely yet. Finally, (3) we could get around this by rendering data rules first, and, in code, only rendering the syntax rule if there is some data to go into it.

I'm going to avoid (3) if at all possible, because it opens up the template injection can of worms again, and we'd still need `{% raw %}{% if %}{% endraw %}` statements in the data rules to prevent them from rendering partially.

[1] In case you're having trouble parsing this mess, when rendered to insert
data rules, and with whitespace added for readability, it turns into this:
{% highlight jinja %}
{% raw %}
{% set contents %}
    {% if subject.mail.0 %}email = {{subject.mail.0}}{% endif %} <-- this is the data rule
{% endset %}
{% if contents %}
    subjectAltName = @{% call openssl.section() %}{{ contents }}{% endcall %}
{% endif %}
{% endraw %}
{% endhighlight %}

[2]
{% highlight jinja %}
{% raw %}
{% set rendersyntax = {} %}

{% set renderdata = {} %}

{# Wrapper for syntax rules. We render the contents of the rule into a
variable, so that if we find that none of the contained data rules rendered we
can suppress the whole syntax rule. That is, a syntax rule is rendered either
if no data rules are specified (unusual) or if at least one of the data rules
rendered successfully. #}
{% macro syntaxrule() -%}
{% do rendersyntax.update(none=true, any=false) -%}
{% set contents -%}
{{ caller() -}}
{% endset -%}
{% if rendersyntax['none'] or rendersyntax['any'] -%}
{{ contents -}}
{% endif -%}
{% endmacro %}

{# Wrapper for data rules. A data rule is rendered only when all of the data
fields it contains have data available. #}
{% macro datarule() -%}
{% do rendersyntax.update(none=false) -%}
{% do renderdata.update(all=true) -%}
{% set contents -%}
{{ caller() -}}
{% endset -%}
{% if renderdata['all'] -%}
{% do rendersyntax.update(any=true) -%}
{{ contents -}}
{% endif -%}
{% endmacro %}

{# Wrapper for fields in data rules. If any value wrapped by this macro
produces an empty string, the entire data rule will be suppressed. #}
{% macro datafield(value) -%}
{% if value -%}
{{ value -}}
{% else -%}
{% do renderdata.update(all=false) -%}
{% endif -%}
{% endmacro %}
{% endraw %}
{% endhighlight %}

[3]
{% highlight jinja %}
{% raw %}
{# List containing rendered sections to be included at end #}
{% set openssl_sections = [] %}

{#
List containing one entry for each section name allocated. Because of
scoping rules, we need to use a list so that it can be a "per-render global"
that gets updated in place. Real globals are shared by all templates with the
same environment, and variables defined in the macro don't persist after the
macro invocation ends.
#}
{% set openssl_section_num = [] %}

{% macro section() -%}
{% set name -%}
sec{{ openssl_section_num|length -}}
{% endset -%}
{% do openssl_section_num.append('') -%}
{% set contents %}{{ caller() }}{% endset -%}
{% if contents -%}
{% set sectiondata = formatsection(name, contents) -%}
{% do openssl_sections.append(sectiondata) -%}
{% endif -%}
{{ name -}}
{% endmacro %}

{% macro formatsection(name, contents) -%}
[ {{ name }} ]
{{ contents -}}
{% endmacro %}
{% endraw %}
{% endhighlight %}
