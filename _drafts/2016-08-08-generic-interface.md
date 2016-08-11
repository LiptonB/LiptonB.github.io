---
title: Generating arbitrary CSR extensions with Openssl
layout: post
highlighter: rouge
tags: freeipa
---

## Contents
{:.no_toc}
* TOC
{:toc}

{% highlight bash %}
{% raw %}
[root@vm-058-019 freeipa]# ipa certmappingrule-add GenericSAN
Description of this mapping rule: subject alt name using generic interface
  Certificate Mapping Rule ID: GenericSAN
  Description of this mapping rule: subject alt name using generic interface
[root@vm-058-019 freeipa]# ipa certmappingrule-add GenericDNS
Description of this mapping rule: DNS subject alt name using generic interface
  Certificate Mapping Rule ID: GenericDNS
  Description of this mapping rule: DNS subject alt name using generic interface
[root@vm-058-019 freeipa]# ipa certtransformationrule-add GenericSAN
Certificate Transformation Rule ID: GenericSANOpenssl
String defining the transformation: {% set extension = true %}2.5.29.17=ASN1:SEQUENCE:{% call openssl.section() %}{{ datarules|join('\n') }}{% endcall %}                          
Name of CSR generation helper: openssl
  Certificate Transformation Rule ID: GenericSANOpenssl
  String defining the transformation: {% set extension = true %}2.5.29.17=ASN1:SEQUENCE:{% call openssl.section() %}{{ datarules|join('\n') }}{% endcall %}
  Name of CSR generation helper: openssl
[root@vm-058-019 freeipa]# ipa certtransformationrule-add GenericDNS
Certificate Transformation Rule ID: GenericDNSOpenssl
String defining the transformation: dns=EXPLICIT:2,IA5STRING:{{ ipa.datafield(subject.krbprincipalname.0|safe_attr("hostname")) }}
Name of CSR generation helper: openssl
  Certificate Transformation Rule ID: GenericDNSOpenssl
  String defining the transformation: dns=EXPLICIT:2,IA5STRING:{{ ipa.datafield(subject.krbprincipalname.0|safe_attr("hostname")) }}
  Name of CSR generation helper: openssl
[root@vm-058-019 freeipa]# ipa certprofile-show --out /tmp/out --mappings-out /tmp/mappings-out caIPAserviceCert
  Profile ID: caIPAserviceCert
  Profile description: Standard profile for network services
  Store issued certificates: TRUE
  Profile configuration stored to: /tmp/out
  Mapping rules stored to: /tmp/mappings-out
[root@vm-058-019 freeipa]# vim /tmp/out  # Remove profileId
[root@vm-058-019 freeipa]# vim /tmp/mappings-out  # Change to the "generic" mapping rules
[root@vm-058-019 freeipa]# ipa certprofile-import --file /tmp/out --mappings-file /tmp/mappings-out genericSAN
Profile description: Host profile using generic interface
Store issued certificates [True]: 
-----------------------------
Imported profile "genericSAN"
-----------------------------
  Profile ID: genericSAN
  Profile description: Host profile using generic interface
  Store issued certificates: TRUE
{% endraw %}
{% endhighlight %}
