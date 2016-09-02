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
We can pretty simply update our data rules to do this partly right, like in
this example:
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
this problem, because the syntax rule intentionally doesn't know what data it
may depend on for different profiles; that all depends on the data rules.

## Current solution: See if something renders
One way to make this work is to build syntax rules so they use jinja2 control
tags to compute the output of any data rules first, then render their own text
only if some data rule rendered successfully. In its raw form, this gets ugly
(see [1] for explanation):

{% highlight jinja %}
{% raw %}
{% raw %}{% set contents %}{%{% endraw %}{% raw %} endraw %}{{ datarules|join('\n') }}
{% raw %}{% endset %}{% if contents %}{%{% endraw %}{% raw %} endraw %}
subjectAltName = @{% call openssl.section() %}{% raw %}{{ contents }}
{%{% endraw %}{% raw %} endraw %}{% endcall %}{% raw %}{% endif %}{%{% endraw %}{% raw %} endraw %}
{% endraw %}
{% endhighlight %}

For comparison, that rule used to look like this:
{% highlight jinja %}
{% raw %}
subjectAltName = @{% call openssl.section() %}
{{ datarules|join('\n') }}{% endcall %}
{% endraw %}
{% endhighlight %}

I think this might be a heavy burden for administrators who want to write new
syntax rules.

However, we can introduce some macros to make this better. One macro,
`syntaxrule`, computes the result of rendering the data rules it contains, but
does not output these results unless a flag is set to true. That flag is
controlled by another macro, `datarule`, which updates the flag to true when
the enclosed data rule renders successfully. We can apply a similar technique
to the fields in the data rules, rendering the rule only if all fields are
present.

Now, the framework can automatically wrap all syntax rules in
`{% raw %}{% call ipa.syntaxrule() %}...{% endcall %}{% endraw %}` and all data
rules in `{% raw %}{% call ipa.datarule() %}...{% endcall %}{% endraw %}`.
Writers of data rules must wrap all field references in `ipa.datafield()` to
mark values that could be missing, such as
`{% raw %}{{ ipa.datafield(subject.mail.0) }}{% endraw %}`,
but no other modifications to the rules are necessary.

This is the way rule suppression is currently implemented.

### Issues
This system seems to be working fairly well, but it has a few drawbacks.

First, the macros to do this are a little arcane, as can be seen in [2], and
can't be commented very well because any whitespace becomes part of the macro
output.  They rely on global variables within the template, but this should be
ok as long as we always nest datafields within datarules within syntaxrules,
and never nest more than once.

Second, syntax rules with multiple assigned data rules present a problem.
Generally we will want the results of those rules to be presented in the output
with some character in between, e.g.
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
--extSAN email:myuser@example.com,
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

## Alternative: Declare data dependencies
Another approach to suppressing syntax rules when none of their data rules are
going to render is to take the "simple approach" of listing the required data
items in an `{% raw %}{% if %}{% endraw %}` statement one step further. We
could amend the schema for data rules to include a record of the included data
item, so that each rule would know its dependencies. Data rules could then be
automatically wrapped so they wouldn't be rendered if this item was
unavailable. Syntax rules could be treated similarly; by querying the
dependencies of all the data rules it was configured to include, the whole
syntax rule could be suppressed if none of those items were available.

In this scheme, the template produced would look like (linebreaks and
indentation added):
{% highlight jinja %}
{% raw %}
{% if subject.mail.0 or subject.inethttpurl.0 %}--extSAN
  {% if subject.mail.0 %}email:{{subject.mail.0|quote}}{% endif %},
  {% if subject.inethttpurl.0 %}uri:{{subject.inethttpurl.0|quote}}{% endif %}
{% endif %}
{% endraw %}
{% endhighlight %}

This takes care of the third problem of the previous solution, because data
rules with missing data will never be evaluated, meaning that superfluous
openssl sections will not be added. However, the second problem still persists,
because the commas and newlines are part of the syntax rule (which is rendered)
not the data rules (some of which aren't rendered).

## Suppressing excess commas and newlines
The challenge with preventing these extra commas and newlines is that they must
be evaluated during the final render, when the subject data is available, not
when the syntax rules are evaluated to build the final template. Using the
`join` filter in the syntax rule is insufficient, because it is evaluated
before that data is available. What we really want is to pass the *output* of
all the data rules to the join filter, *at final render time*.

This is not a polished solution, but an image of what this could look like is
for the data rule to be:
{% highlight jinja %}
{% raw %}
--extSAN {{datarules|filternonempty("join(',')")}}
{% endraw %}
{% endhighlight %}
Which would create a final template like:
{% highlight jinja %}
{% raw %}
{% filternonempty join(',') %}
<data rule 1>
{% filterpart %}
<data rule 2>
{% endfilternonempty %}
{% endraw %}
{% endhighlight %}
And the `filternonempty` tag would be implemented so the effect of this would
be approximately:
{% highlight jinja %}
{% raw %}
{% set parts = [] %}
{% set part %}
<data rule 1>
{% endset %}
{% if part %}{% do parts.append(part %}{% endif %}
{% set part %}
<data rule 2>
{% endset %}
{% if part %}{% do parts.append(part %}{% endif %}
{{ parts|join(',') }}
{% endraw %}
{% endhighlight %}
I think this is doable, but I don't have a prototype yet.

## Conclusions
The current implementation is working ok, but the "Declaring data dependencies"
solution is also appealing. Recording in data rules what data they depend on is
only slightly more involved than wrapping that reference in `ipa.datafield()`,
and could also be useful for other purposes. Plus, it would get rid of the
empty sections in openssl configs, as well as some of the complex macros.

The extra templating and new tags required to get rid of extra commas and
newlines don't seem worth it to me, unless we discover a version of openssl or
certutil that can't consume the current output.

Finally, I think the number of hoops needing to be jumped through to fine-tune
the output format hint at this "template interpolation" approach being less
successful than originally expected. While it was expected that inserting data
rule templates into syntax rule templates and rendering the whole thing would
produce similar results to rendering data rules first and inserting the output
into syntax rules, that is not turning out to be the case. It might be wise to
reconsider the simpler option - it may be easier to implement reliable jinja2
template markup escaping than to build templates smart enough to handle any
combination of data that's available.

## Appendix
{:.no_toc}
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
