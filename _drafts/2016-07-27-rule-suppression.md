---
title: Suppressing rules with insufficient data
layout: post
highlighter: rouge
tags: freeipa
---

## Contents
{:.no_toc}
* TOC
{:toc}

Sometimes you might want to generate a certificate for a principal that doesn't have all the fields referenced in the profile. This could be an error (e.g. used the "user" profile for a "service" principal) or just the way the data is (e.g. the principal has no email address, or the requesting user has no access to that field). We want to handle this cleanly by omitting the sections of config that have missing data.

We can pretty simply update our data rules to do this partly right, like in this example:
'{% if subject.fqdn.0 is defined %}DNS = {{subject.fqdn.0}}{% endif %}'
However, if *none* of the data rules for a field has any data, we need to avoid rendering the syntax rule for that field as well, otherwise we get weird empty sections that openssl doesn't like. This is harder, because the syntax rule in the database intentionally doesn't know what data it may depend on for different profiles; that all depends on the data rules. We can make it work by having syntax rules insert templating to compute the data rules first, then render their text only if some data rendered. That looks like this [1]:
{% set extension = true %}{% raw %}{% set contents %}{% endraw %}{{ datarules|join(\'\\n\') }}{% raw %}{% endset %}{% if contents %}{% endraw %}subjectAltName = @{% call openssl.section() %}{% raw %}{{ contents }}{% endraw %}{% endcall %}{% raw %}{% endif %}{% endraw %}

For comparison, that rule used to look like this:
{% set extension = true %}subjectAltName = @{% call openssl.section() %}{{ datarules|join(\'\\n\') }}{% endcall %}

I think this might be a heavy burden for administrators who want to write new syntax rules.

One way I can think of to get around this is (1) to have data rules declare in LDAP what data they use. Then the renderer can automatically generate {% if %} statements around both the data rules and the syntax rules based on the availability of data referenced in the data rules. Then no manual modifications to the rules are necessary. Another option (2) is that it may be possible to use macros or jinja2 extensions to add some syntactic sugar for this situation, though I haven't figured out quite how to do that nicely yet. Finally, (3) we could get around this by rendering data rules first, and, in code, only rendering the syntax rule if there is some data to go into it.

I'm going to avoid (3) if at all possible, because it opens up the template injection can of worms again, and we'd still need {% if %} statements in the data rules to prevent them from rendering partially.

[1] In case you're having trouble parsing this mess, when rendered to insert data rules, and with linebreaks added for readability, it turns into this:
{% set contents %}
    {% if subject.mail.0 is defined %}email = {{subject.mail.0}}{% endif %} <-- this is the data rule
{% endset %}
{% if contents %}
    subjectAltName = @{% call openssl.section() %}{{ contents }}{% endcall %}
{% endif %}
