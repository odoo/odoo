# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

MAIL_TEMPLATE = """Return-Path: <whatever-2a840@postmaster.twitter.com>
To: {to}
cc: {cc}
Received: by mail1.openerp.com (Postfix, from userid 10002)
    id 5DF9ABFB2A; Fri, 10 Aug 2012 16:16:39 +0200 (CEST)
From: {email_from}
Subject: {subject}
MIME-Version: 1.0
Content-Type: multipart/alternative;
    boundary="----=_Part_4200734_24778174.1344608186754"
Date: Fri, 10 Aug 2012 14:16:26 +0000
Message-ID: {msg_id}
{extra}
------=_Part_4200734_24778174.1344608186754
Content-Type: text/plain; charset=utf-8
Content-Transfer-Encoding: quoted-printable

Please call me as soon as possible this afternoon!

--
Sylvie
------=_Part_4200734_24778174.1344608186754
Content-Type: text/html; charset=utf-8
Content-Transfer-Encoding: quoted-printable

<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
 <head>=20
  <meta http-equiv=3D"Content-Type" content=3D"text/html; charset=3Dutf-8" />
 </head>=20
 <body style=3D"margin: 0; padding: 0; background: #ffffff;-webkit-text-size-adjust: 100%;">=20

  <p>Please call me as soon as possible this afternoon!</p>

  <p>--<br/>
     Sylvie
  <p>
 </body>
</html>
------=_Part_4200734_24778174.1344608186754--
"""

MAIL_TEMPLATE_EXTRA_HTML = """Return-Path: <whatever-2a840@postmaster.twitter.com>
To: {to}
cc: {cc}
Received: by mail1.openerp.com (Postfix, from userid 10002)
    id 5DF9ABFB2A; Fri, 10 Aug 2012 16:16:39 +0200 (CEST)
From: {email_from}
Subject: {subject}
MIME-Version: 1.0
Content-Type: multipart/alternative;
    boundary="----=_Part_4200734_24778174.1344608186754"
Date: Fri, 10 Aug 2012 14:16:26 +0000
Message-ID: {msg_id}
{extra}
------=_Part_4200734_24778174.1344608186754
Content-Type: text/plain; charset=utf-8
Content-Transfer-Encoding: quoted-printable

Please call me as soon as possible this afternoon!

--
Sylvie
------=_Part_4200734_24778174.1344608186754
Content-Type: text/html; charset=utf-8
Content-Transfer-Encoding: quoted-printable

<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
 <head>=20
  <meta http-equiv=3D"Content-Type" content=3D"text/html; charset=3Dutf-8" />
 </head>=20
 <body style=3D"margin: 0; padding: 0; background: #ffffff;-webkit-text-size-adjust: 100%;">=20

  <p>Please call me as soon as possible this afternoon!</p>
  {extra_html}

  <p>--<br/>
     Sylvie
  <p>
 </body>
</html>
------=_Part_4200734_24778174.1344608186754--
"""


MAIL_TEMPLATE_PLAINTEXT = """Return-Path: <whatever-2a840@postmaster.twitter.com>
To: {to}
Received: by mail1.openerp.com (Postfix, from userid 10002)
    id 5DF9ABFB2A; Fri, 10 Aug 2012 16:16:39 +0200 (CEST)
From: {email_from}
Subject: {subject}
MIME-Version: 1.0
Content-Type: text/plain
Date: Fri, 10 Aug 2012 14:16:26 +0000
Message-ID: {msg_id}
{extra}

Please call me as soon as possible this afternoon!

--
Sylvie
"""

MAIL_MULTIPART_MIXED = """Return-Path: <ignasse.carambar@gmail.com>
X-Original-To: raoul@grosbedon.fr
Delivered-To: raoul@grosbedon.fr
Received: by mail1.grosbedon.com (Postfix, from userid 10002)
    id E8166BFACA; Fri, 23 Aug 2013 13:18:01 +0200 (CEST)
X-Spam-Checker-Version: SpamAssassin 3.3.1 (2010-03-16) on mail1.grosbedon.com
X-Spam-Level:
X-Spam-Status: No, score=-2.6 required=5.0 tests=BAYES_00,FREEMAIL_FROM,
    HTML_MESSAGE,RCVD_IN_DNSWL_LOW autolearn=unavailable version=3.3.1
Received: from mail-ie0-f173.google.com (mail-ie0-f173.google.com [209.85.223.173])
    by mail1.grosbedon.com (Postfix) with ESMTPS id 9BBD7BFAAA
    for <raoul@openerp.fr>; Fri, 23 Aug 2013 13:17:55 +0200 (CEST)
Received: by mail-ie0-f173.google.com with SMTP id qd12so575130ieb.4
        for <raoul@grosbedon.fr>; Fri, 23 Aug 2013 04:17:54 -0700 (PDT)
DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed;
        d=gmail.com; s=20120113;
        h=mime-version:date:message-id:subject:from:to:content-type;
        bh=dMNHV52EC7GAa7+9a9tqwT9joy9z+1950J/3A6/M/hU=;
        b=DGuv0VjegdSrEe36ADC8XZ9Inrb3Iu+3/52Bm+caltddXFH9yewTr0JkCRQaJgMwG9
         qXTQgP8qu/VFEbCh6scu5ZgU1hknzlNCYr3LT+Ih7dAZVUEHUJdwjzUU1LFV95G2RaCd
         /Lwff6CibuUvrA+0CBO7IRKW0Sn5j0mukYu8dbaKsm6ou6HqS8Nuj85fcXJfHSHp6Y9u
         dmE8jBh3fHCHF/nAvU+8aBNSIzl1FGfiBYb2jCoapIuVFitKR4q5cuoodpkH9XqqtOdH
         DG+YjEyi8L7uvdOfN16eMr7hfUkQei1yQgvGu9/5kXoHg9+Gx6VsZIycn4zoaXTV3Nhn
         nu4g==
MIME-Version: 1.0
X-Received: by 10.50.124.65 with SMTP id mg1mr1144467igb.43.1377256674216;
 Fri, 23 Aug 2013 04:17:54 -0700 (PDT)
Received: by 10.43.99.71 with HTTP; Fri, 23 Aug 2013 04:17:54 -0700 (PDT)
Date: Fri, 23 Aug 2013 13:17:54 +0200
Message-ID: <CAP76m_V4BY2F7DWHzwfjteyhW8L2LJswVshtmtVym+LUJ=rASQ@mail.gmail.com>
Subject: Test mail multipart/mixed
From: =?ISO-8859-1?Q?Raoul Grosbedon=E9e?= <ignasse.carambar@gmail.com>
To: Followers of ASUSTeK-Joseph-Walters <raoul@grosbedon.fr>
Content-Type: multipart/mixed; boundary=089e01536c4ed4d17204e49b8e96

--089e01536c4ed4d17204e49b8e96
Content-Type: multipart/alternative; boundary=089e01536c4ed4d16d04e49b8e94

--089e01536c4ed4d16d04e49b8e94
Content-Type: text/plain; charset=ISO-8859-1

Should create a multipart/mixed: from gmail, *bold*, with attachment.

--
Marcel Boitempoils.

--089e01536c4ed4d16d04e49b8e94
Content-Type: text/html; charset=ISO-8859-1

<div dir="ltr">Should create a multipart/mixed: from gmail, <b>bold</b>, with attachment.<br clear="all"><div><br></div>-- <br>Marcel Boitempoils.</div>

--089e01536c4ed4d16d04e49b8e94--
--089e01536c4ed4d17204e49b8e96
Content-Type: text/plain; charset=US-ASCII; name="test.txt"
Content-Disposition: attachment; filename="test.txt"
Content-Transfer-Encoding: base64
X-Attachment-Id: f_hkpb27k00

dGVzdAo=
--089e01536c4ed4d17204e49b8e96--"""

MAIL_MULTIPART_MIXED_TWO = """X-Original-To: raoul@grosbedon.fr
Delivered-To: raoul@grosbedon.fr
Received: by mail1.grosbedon.com (Postfix, from userid 10002)
    id E8166BFACA; Fri, 23 Aug 2013 13:18:01 +0200 (CEST)
From: "Bruce Wayne" <bruce@wayneenterprises.com>
Content-Type: multipart/alternative;
 boundary="Apple-Mail=_9331E12B-8BD2-4EC7-B53E-01F3FBEC9227"
Message-Id: <6BB1FAB2-2104-438E-9447-07AE2C8C4A92@sexample.com>
Mime-Version: 1.0 (Mac OS X Mail 7.3 \(1878.6\))

--Apple-Mail=_9331E12B-8BD2-4EC7-B53E-01F3FBEC9227
Content-Transfer-Encoding: 7bit
Content-Type: text/plain;
    charset=us-ascii

First and second part

--Apple-Mail=_9331E12B-8BD2-4EC7-B53E-01F3FBEC9227
Content-Type: multipart/mixed;
 boundary="Apple-Mail=_CA6C687E-6AA0-411E-B0FE-F0ABB4CFED1F"

--Apple-Mail=_CA6C687E-6AA0-411E-B0FE-F0ABB4CFED1F
Content-Transfer-Encoding: 7bit
Content-Type: text/html;
    charset=us-ascii

<html><head></head><body>First part</body></html>

--Apple-Mail=_CA6C687E-6AA0-411E-B0FE-F0ABB4CFED1F
Content-Disposition: inline;
    filename=thetruth.pdf
Content-Type: application/pdf;
    name="thetruth.pdf"
Content-Transfer-Encoding: base64

SSBhbSB0aGUgQmF0TWFuCg==

--Apple-Mail=_CA6C687E-6AA0-411E-B0FE-F0ABB4CFED1F
Content-Transfer-Encoding: 7bit
Content-Type: text/html;
    charset=us-ascii

<html><head></head><body>Second part</body></html>
--Apple-Mail=_CA6C687E-6AA0-411E-B0FE-F0ABB4CFED1F--

--Apple-Mail=_9331E12B-8BD2-4EC7-B53E-01F3FBEC9227--
"""


MAIL_MULTIPART_BINARY_OCTET_STREAM = """X-Original-To: raoul@grosbedon.fr
Delivered-To: raoul@grosbedon.fr
Received: by mail1.grosbedon.com (Postfix, from userid 10002)
    id E8166BFACA; Fri, 10 Nov 2021 06:04:01 +0200 (CEST)
From: "Bruce Wayne" <bruce@wayneenterprises.com>
Content-Type: multipart/alternative;
 boundary="Apple-Mail=_9331E12B-8BD2-4EC7-B53E-01F3FBEC9227"
Message-Id: <6BB1FAB2-2104-438E-9447-07AE2C8C4A92@sexample.com>
Mime-Version: 1.0 (Mac OS X Mail 7.3 \(1878.6\))

--Apple-Mail=_9331E12B-8BD2-4EC7-B53E-01F3FBEC9227
Content-Transfer-Encoding: 7bit
Content-Type: text/plain;
    charset=us-ascii

Here is my crypto wallet private key that contains 100k USDT

--Apple-Mail=_9331E12B-8BD2-4EC7-B53E-01F3FBEC9227
Content-Disposition: attachment; 
 filename="private_key_crypto_wallet_100K_USDT.pdf"
Content-Type: binary/octet-stream;
 name="private_key_crypto_wallet_100K_USDT.pdf"
Content-Transfer-Encoding: base64

JVBERi0xLjcNJc3K0qkNMSAwIG9iago8PAovTWV0YWRhdGEgNCAwIFIKL1BhZ2VMYXlvdXQgL09u
ZUNvbHVtbgovUGFnZU1vZGUgL1VzZU5vbmUKL1BhZ2VzIDIgMCBSCi9UeXBlIC9DYXRhbG9nCj4+
CmVuZG9iagoyIDAgb2JqCjw8Ci9Db3VudCAxCi9LaWRzIFsgNiAwIFIgXQovVHlwZSAvUGFnZXMK
Pj4KZW5kb2JqCjMgMCBvYmoKPDwKL0NyZWF0aW9uRGF0ZSAoRDoyMDIyMTEyMzEzMDA1NSswMCcw
MCcpCi9Nb2REYXRlIChEOjIwMjIxMTIzMTMwMDU1KzAwJzAwJykKL1Byb2R1Y2VyICj+/1wwMDBB
XDAwMHNcMDAwY1wwMDBlXDAwMG5cMDAwc1wwMDBpXDAwMG9cMDAwXDA0MFwwMDBTXDAwMHlcMDAw
c1wwMDB0XDAwMGVcMDAwbVwwMDBcMDQwXDAwMFNcMDAwSVwwMDBBXDAwMFwwNDBcMDAwQ1wwMDBv
XDAwMHBcMDAweVwwMDByXDAwMGlcMDAwZ1wwMDBoXDAwMHRcMDAwXDA0MFwwMDBcMDUwXDAwMGNc
MDAwXDA1MVwwMDBcMDQwXDAwMDJcMDAwMFwwMDAxXDAwMDgpCj4+CmVuZG9iago0IDAgb2JqCjw8
Ci9MZW5ndGggNSAwIFIKL1N1YnR5cGUgL1hNTAovVHlwZSAvTWV0YWRhdGEKPj4Kc3RyZWFtDQo8
P3hwYWNrZXQgYmVnaW49Iu+7vyIgaWQ9Ilc1TTBNcENlaGlIenJlU3pOVGN6a2M5ZCI/Pgo8eDp4
bXBtZXRhIHhtbG5zOng9ImFkb2JlOm5zOm1ldGEvIiB4OnhtcHRrPSIzLjEtNzAxIj4KPHJkZjpS
REYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMj
Ij4KPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6cGRmPSJodHRwOi8vbnMuYWRv
YmUuY29tL3BkZi8xLjMvIj4KPHBkZjpQcm9kdWNlcj5Bc2NlbnNpbyBTeXN0ZW0gU0lBIENvcHly
aWdodCAoYykgMjAxODwvcGRmOlByb2R1Y2VyPgo8L3JkZjpEZXNjcmlwdGlvbj4KPHJkZjpEZXNj
cmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8x
LjAvIj4KPHhtcDpDcmVhdG9yVG9vbD5PTkxZT0ZGSUNFPC94bXA6Q3JlYXRvclRvb2w+Cjx4bXA6
Q3JlYXRlRGF0ZT4yMDIyLTExLTIzVDEzOjAwOjU1KzAwOjAwPC94bXA6Q3JlYXRlRGF0ZT48eG1w
Ok1vZGlmeURhdGU+MjAyMi0xMS0yM1QxMzowMDo1NSswMDowMDwveG1wOk1vZGlmeURhdGU+PC9y
ZGY6RGVzY3JpcHRpb24+CjwvcmRmOlJERj4KPC94OnhtcG1ldGE+PD94cGFja2V0IGVuZD0idyI/
PgplbmRzdHJlYW0KZW5kb2JqCjUgMCBvYmoKNjI5CmVuZG9iago2IDAgb2JqCjw8Ci9Bbm5vdHMg
WyA5IDAgUiBdCi9Db250ZW50cyA3IDAgUgovTWVkaWFCb3ggWyAwIDAgNTk1LjI5OTk5IDg0MS45
MDAwMiBdCi9QYXJlbnQgMiAwIFIKL1Jlc291cmNlcyA8PAovRXh0R1N0YXRlIDw8Ci9FLTE4NzY5
ODk4NDAgMTkgMCBSCj4+Ci9Gb250IDw8Ci9GMSAxMCAwIFIKPj4KL1Byb2NTZXQgWyAvUERGIC9U
ZXh0IC9JbWFnZUIgL0ltYWdlQyAvSW1hZ2VJIF0KPj4KL1R5cGUgL1BhZ2UKPj4KZW5kb2JqCjcg
MCBvYmoKPDwKL0ZpbHRlciBbIC9GbGF0ZURlY29kZSBdCi9MZW5ndGggOCAwIFIKPj4Kc3RyZWFt
DQp4nGWQwU4DMQxE7/4K/0BTO4kdR1pVamGL1BuwN8StohKCQ9sDv48DgW4h0VOU0Xg08hE2Eyy3
jBxxegFCv0GIq+LpcPV9uAOTQIJFOdSqVnHaw9NAROzETnKyI452ygxzqrN2Nn2mvTfO7WpBwVIh
Hrpz/FayytBntpdMpit//Of3XsxzD7uHU1OqZilN8a4sPe8nt2FfczlKbC5vzOtLfk+T1fO0g3GC
ezj+3dVyXLAVrVYtEx7OQEH9CH64cweMr7/r9DZiGvEdUk6hqBabqW/w6Pmfef1U9AplbmRzdHJl
YW0KZW5kb2JqCjggMCBvYmoKMjE4CmVuZG9iago5IDAgb2JqCjw8Ci9BIDw8Ci9TIC9VUkkKL1R5
cGUgL0FjdGlvbgovVVJJIChodHRwczpcMDU3XDA1N3d3dy55b3V0dWJlLmNvbVwwNTd3YXRjaD92
PWRRdzR3OVdnWGNRKQo+PgovQlMgPDwKL1cgMAo+PgovRiA0Ci9SZWN0IFsgODUuMDQ5OTcgNzU5
LjQwMTI1IDM0My43NjY3NSA3NzMuMjAwMDEgXQovU3VidHlwZSAvTGluawovVHlwZSAvQW5ub3QK
Pj4KZW5kb2JqCjEwIDAgb2JqCjw8Ci9CYXNlRm9udCAvQkFBQUFBK0xpYmVyYXRpb24jMjBTZXJp
ZgovRGVzY2VuZGFudEZvbnRzIFsgMTEgMCBSIF0KL0VuY29kaW5nIC9JZGVudGl0eS1ICi9TdWJ0
eXBlIC9UeXBlMAovVG9Vbmljb2RlIDEyIDAgUgovVHlwZSAvRm9udAo+PgplbmRvYmoKMTEgMCBv
YmoKPDwKL0Jhc2VGb250IC9CQUFBQUErTGliZXJhdGlvbiMyMFNlcmlmCi9DSURTeXN0ZW1JbmZv
IDw8Ci9PcmRlcmluZyAoSWRlbnRpdHkpCi9SZWdpc3RyeSAoQWRvYmUpCi9TdXBwbGVtZW50IDAK
Pj4KL0NJRFRvR0lETWFwIDE3IDAgUgovRm9udERlc2NyaXB0b3IgMTQgMCBSCi9TdWJ0eXBlIC9D
SURGb250VHlwZTIKL1R5cGUgL0ZvbnQKL1cgWyAwIFsgMzY1IDUwMCAyNzcgNTAwIDM4OSAyNzcg
Mjc3IDcyMiAyNTAgNTAwIDUwMCA1MDAgNTAwIDQ0MyA0NDMgNzc3IDQ0MyA0NDMgNTAwIDU2MyA1
MDAgNzIyIDUwMCA1MDAgOTQzIDUwMCA3MjIgXSBdCj4+CmVuZG9iagoxMiAwIG9iago8PAovRmls
dGVyIFsgL0ZsYXRlRGVjb2RlIF0KL0xlbmd0aCAxMyAwIFIKPj4Kc3RyZWFtDQp4nF2SzW6DMBCE
7zyFj+khIsYBEgkhpfmROPRHpX0AYi8pUjGWIQfevsZjpVItAfqYHduj3fhYnSrdTSx+t4OsaWJt
p5WlcbhbSexKt05HPGGqk1Mg/5Z9Y6LYmet5nKivdDtERcHiDyeOk53Z6qCGKz1FLH6zimynb2z1
dayXH/XdmB/qSU9sE7GyZIpat9dLY16bnljsnetKuYJumtfO9VfxORtiiWeO+8hB0WgaSbbRN4qK
jVslKy5ulRFp9U9Pctiurfxu7KPcfzxxT9kOlHjKtyABCpVbkAClnsQBlHlKLqAclTloB+0M2kPb
gw44PfieoaWgI7QEdAIF7QwKd7mATp448mUchHwCJ/CQLwMhnwg+5MuQnSNfGnZBPhE05BPIwJEv
RVqOfFkg5Et3vjWhB0uTlnF6TIC8W+ua72fOd33pd6fpMZZmMIvLP7/gs7YjCmVuZHN0cmVhbQpl
bmRvYmoKMTMgMCBvYmoKMzQwCmVuZG9iagoxNCAwIG9iago8PAovQXNjZW50IDE0MjAKL0NhcEhl
aWdodCAxMzQxCi9EZXNjZW50IC00NDIKL0ZsYWdzIDQKL0ZvbnRCQm94IFsgLTM2MiAtNjIxIDIw
NjIgMjAxMCBdCi9Gb250RmlsZTIgMTUgMCBSCi9Gb250TmFtZSAvQkFBQUFBK0xpYmVyYXRpb24j
MjBTZXJpZgovRm9udFdlaWdodCA0MDAKL0l0YWxpY0FuZ2xlIDAKL1N0ZW1WIDAKL1R5cGUgL0Zv
bnREZXNjcmlwdG9yCj4+CmVuZG9iagoxNSAwIG9iago8PAovRmlsdGVyIFsgL0ZsYXRlRGVjb2Rl
IF0KL0xlbmd0aCAxNiAwIFIKL0xlbmd0aDEgMjUyMjQKPj4Kc3RyZWFtDQp4nO18eVxbx7XwnLm6
2kECxGUVEpYAgwCBxGXxImRWYRxbZrHBBBsBAmSzWYAdZ6lJ4sSxHTdu47qOs7l5rpsm6YvsuKnT
tI3bl7TNl2bp1yxNs7mtuyZu/NI0r01i+M5cXcnYTfvet/x+3z9PYnTOzJw558yZc+bM6AIECCEJ
ZJZwxL+m3en624c3fgVb3sTSNzAWmFQ0cJsJgWVYXzWwbdrqqfN+jPXbCKHC0OTw2NTPbBFCuKOE
qPjh0R1Dm36eeIAQ7YOELK4YCQYG//zNN54jxMX4VY5gQ6JF9UdC3Cas20fGpq951fmCiPVqHLNr
dGIgcHva12cJWf4dQviGscA1k6op9VJC6pGcWMcDY8G3nzH9AutWQtTbJiempo9NCScJaT1MiOn6
yXBw0nt39w9QdeRPpwmn2AcHCI+8jvBu1DovClHbQTgGPKVKjlfwlFMcJfRRP7nmEyK/yle01xMv
yf2E8rfPNYFblQtP9hFy/zuv4ehH+OVMG0LxEwhIA/REifRSA75ayXrSTtYRM0kmG0gSuZq0kS7S
SHykifhJA1lEunF8M6kgaSSbLCEryVJ+P0klPuRsIJPS52Uv7hGSweD8e5d/zq2a/5j8P3ypo+Aw
OU5Okf3kddIrdzC9Q2QGWxa+vk9+iq3s5cd5PkT2/gO2j5DT2B+l6yN3kLv+AZ2ffJk8Rn50mRQ/
GSPXoS7fJK9DOXkWLTxBPgA1uZE8g1w/wLarPosVTcSPIQkdWtD6Brmb7iMr6Tms3MV6qJMaydPk
HtiInKdxnvvjM172d0x3kxvws52MkG2ISy9++ae/IJr5P+OsbsB1vImsIKMLRnwH7ue0uH4d5H60
6felNmesU+XjNtPHKb14J1a+QIaxBADnTvdzK0gDnwSnCPE2dnd1drS3rfWvWX3VqtaVLb7mpsaG
+roV3lrP8mVLl9RUV1WK5WXO0pLixQX5eXbbolxLuinJaEhM0Gk1apWSV3AUSHGjranPGsnviyjy
bT5fCavbAtgQWNDQF7FiU9PlNBFrn0RmvZzSi5RDV1B6o5TeOCUYrcvIspJia6PNGnm+wWY9DRvW
diG+v8HWbY2cl/CrJFyRL1USsJKbiyOsjekjDdYI9FkbI03bRvY29jUgvxM6bb2tPqgtKSYntDpE
dYhFFtsmT8BiD0gIXdy45AQl6gQmNsLlNQYGI/61XY0NWbm53SXFLZFEW4PUReollhFlfUQlsbSG
mOpkn/VE8Zm9t582kv4+h37QNhi4uivCBXDsXq5x797dkSRHpNDWECm89lw6zjwYKbY1NEYcjGtr
W1xO6yWREOHzjDbr3r8QnI7t/HuXtwTkFmWe8S+EoU1o3r17m2zWpr19ewOn52f7bVajbe8JvX7v
ZCNamPi7cNTp+W/vy4o03d4dMfaNwBJ5sk1trZGUtT1dEZrXZB0JYAv+1Npyq7Nyk7pjNP5/1E3Q
EGgOtGluLpv4vtNe0o+VyOzarmjdSvqzThKv09EdoX2s50ysJ7WT9czGeuLD+2y4mq3tXXsjiryW
QVsj2nhfIDLbj/60mS2FzRhJ/Cgr17Y3Ocla4+yWaK2oVctgyBrh89EsOGrhAPQUNmSvUaokfhQF
57NQQH5SsrXGhmwYn0ZbY5/8s20kHRlYS4ojPkd06Tu6It4GRLwBeY0aT5Q5cUSgD5co1CAtX8Rp
m4yYbHXx9WRqNYbau6Qh8rCIqT6CiVIeFXE2NjDJ1sa9fQ1RFRgv29quJ4h7/uyJCmvWY27c9bsb
GLFQj36V37i3a3AoYunLGsRIG7J2ZeVGvN24wN22rmA3czS0UOFZFJcrSYzQ+o6u1nZb69oNXdWy
ItEOxk6R13gFG1tXVpQNulxEnae2dtEsrhsJjdhgbULEVrcMPyOqPDUWIxpcamWuWrfM2gVZJEaN
akQKrY3BBpmO1S9jyjN3qvfFuClZFfnU+7Jyu3Ojr5Jiit1WWTCOUDOj+mJdXB7uBNhGkY3UxGyZ
znze2mUL2rptI9aI19/F5sbMI1lZNoZkc3mtOi6rLTAWmonkYneswowZaXJkLTRupFmqx6u+K7pb
Yt3WvWpba/textwmMySoeUuEMBf2VidlSdHP4tnWFMAgxoiW4nnvCa+XxfIIC9u9tpbBvbb2rmUS
Ne4gN2Rdy2Qlk1Zo7agrKcbNrO6EDW5be8ILt7Vv6HrCiIeP2zq6TlKg9X113Sfs2Nf1hBVzhdRK
WStrZBUrqzBObVhRS/RZT3gJmZV6FVKDVB84DURqU8fagAycptE2Y6yNYpsi2uaV2tgLVyl9BG2M
+3ejdZCtz/XdI3v7upmPEwEtgj8QAZsHrWPznACq1Ee0tmBdRGerY+21rL022q5k7Sr0DBCgpPja
vcZG21/SS6TUjecmQgf5TjypqkjpCSDOZSdVCvV51wkl/+aykxxFlJzgWDPPmk+qlJpPl50E1u5O
yk3Ky03KbaDWOTscnhvhOz9+uEHxPGEHtt3zv4Yd5BWSQgq8GeQQ0QLRGrUXtJwM1FrD3XwKqT0P
zo29W8Pny8vyTInUtqiUihUe6nblUNiRYi3JyCy2pqRYizMzSqwpV2cU56ak5BZnsAp2SgfD+fdo
Dd+E+q96Aiu/9xZkWX1aClqaSYvot+kf6cdUqaHp2Ep4WNbHH+WplwMOTs9HvqVO8AFVoI61teB0
OHu3buwtL3OgPo40G7gHB+G1fhO/QbLTYjxvnOUbiJYkkhu9Rn21YPaJykZlp5JbpwTl6fkL3uSU
TJ/R6DdSv3HSGDFeMCoSTqNC5UKWL0HhNWX4FFqtGsYTlQTX3opr7aeT9CiNULWaqvnEGcJxoFMp
IR3VcSfXON3nXS5mHTdDnE6H29G7FdXr3UockGRLyhXBneROBRvkckWPXHyI3jH1+Nx9/JwVfgMF
c69DwS3c4U/Dd3Cui72of938e3jGXoXzqCZ3e8eq0vUG354COGKBnMWILs2BLMEh0M0J1yYcSeC0
+Zn5RflcRe6EdolxiX8J9S+ZXBJZcmGJoniCmEwTZCeyzK2oKJ/W2PfY77Jzdnth9lSSRXAKtQIn
CEkZhVNK/lb+EM+peRWp3dh7vtbt7DWex2n1nncZnwVnr9tpPN+71fj2eVd5GemF3t5eB/6kRFcf
klNNiQrbovwC0Z2Ww7ldHlqVCMw9YJEy1ZSDNJVVFaW0btnk0cHw8TGxoCkwfXNj1x0NK2wpTreY
0bRjQxVfd6S74/ZgFZy8cUdubc/Sul2e7GX93LHh+7dU+b82N3fixueOjDVYkpJ+f0CTqOOX7vrZ
4bwyd/AQfPuxr7eFm63ZGXe+86XWaJw8gP58J/d95s/kgW9VFDYUdhRyhafnz3gT6pt8pNBYSJe9
XAis5fHqpb4DUdSbU1LmO1sIpwqfLny5kCsrBMpIrYXc0cJIIZVIkhOMPhM5lDOpndUe0HIRLWix
+bHcfB+D3hR0n/tZ9IBam3G3zSiHTTRweh2O3jC6BzrFpq1btzrCjvBGNOPfB1PSlcF1JwbVpeCK
wsvqVwYb/dmlXqkjapcheFBh4R6U9o8mb5nSSstoH/q1wkAtFPc9nl3qvHhBURD6jVkMPOU3LCow
qEDl1Rt9KuJE1c+/3XtecgicEDoDpKJrY1FYPm3mnvi0mSYODcGRoSFJ3ub5X3M16McW4qbf985v
TjqSRHmrPslnPbSz6I6i+4u4IgspogAp6rsqM5oyKJ+RmpGXwam5DPETEf4gwhsiiN6/ferbIl4n
7hO5GrFFpFmiQ6Qa1v03kSLBsyI8ych+90ckg24RloqtIi0RIUuEBBHeRVb0efEtkYqzP3/DNybe
wLCfvuLDvpfE2Z+86Puu+LxIHxbhLhGYFNorjom0BVnOPvUD30VJjyfF58Q3RO5e8Rsi3SHuEWmP
uEWkVzFZUMgoH4n4UI+7xYfFJ0VuvwiwUwSJRpw9+i8+nQj3v+P9ifi+OC9yz4nwlAgPs1EHD/sk
ZZ2SsgYR5pm+8KL4DlPoSZHeL8I+ESbEnUwi1IprkKH3czf63kFWNMpon8ikcigPZ79Jnr1FdIoU
pU5Is5f4id5gyDchgkNcKvaInEG0iFSe1qPMfO3rfGtE0IlZIp2PzeRdUbFLhEkROsRBkZaJYBeB
iEaRekTm7vnVy30vifC0CBERgwU7rKJXVBAEfnFSjIhnxLOiSiItdLpQaTgggqQaEUFdlgKGFEix
3EupQJx356UkJSXcKygwXtzO2osvJNU4maP1op9h6GwNbwqHww6pwl4YP1u3spZwON7GyGKvcLQv
LIVY76bL+qR2iZmDdcqNC0cZ396EXM+jCm738y7cBdlWDjauysOJuJHZFikNYBM94HYJuPVRA6Rc
GbKn/Zl32JcVp2dUX12/bMBmq2va3/Hyy7mt16yvuerK6IWNsNqsstWHrmoZ8pqzU4/NpaQ/8mDT
zuHW5ISLH/9dHqWkY+4UfwzjKgXv2g9+sz1vII/msey1BZNDnx368sCW585rz+Py8MhItVUrq6g2
AbQqwBs1j3nLtqTA5HRqe0gOpOXUk3qotdZ76ynpKTN5TdRgspicJs5U6L2jAipmfTZYYuM3XbP8
tuV0eYph0/aM3Rk0A5cJ00Tvebe7N/PN3szn2Uqdx5RsfBvTh9uZlFxTU152aWUImk9KBB4aNWAi
VVUkMwNGswdVxRJHaiLHDOkEKYMAhbyioUduuumR4aKiYQaHin66/viH993154c2OHt2dbocK1cs
y1Glpwu8rrhqWVZNz/qemsLkwoy7PnhoA73v9l/dv27d/b+6fd8v7+3svPeX+04C9+DatQ/OXTw5
+/y9kzZP5eryNMBXHa/Xq821weYKStseAgWRzkV0/peqPfxyYqIvek+qDJCWCNclQFcCOBJghId0
CjyAmuOhTafXbVDyJqWST4A2Bae4Wp9g0usTKLQlGhI3cNTEcbjNtRkNxqsJmJD3rXpQ6Qv0Vfrt
eoVmvWHYQCsNTQaqMqQZCgycVs8ZDJyeUxLhWQGeFODrAtwtwB4B8oV1wjaBe1X4rUBPCU8L9LjU
fJ0AQwJ0CNAkgEbIEAoF7lcCi7vR19/2HRSOCfRWAdoEsAsVQgNL+kAF+ECAcwK8KsAxgbHidgh7
BIoMCgUQhHwUc6vwuMBrBHjoD8LfBCp4v/qg7znhDYYdudeHIkNM3jqB5guVSMkxgY8duNMnCc7b
vc9nEkApwEcCvCwA4/ZDgesWoJW1CjiEC0sjtkxERziHQr4nBLhJAJgUYJCNOifQfcLdwsMCN8lm
NyhQrwAmgc1CkuYtxny+TwCv4BeoAltpzYfMXs+xmkk4KHAmYVqa3MsCLw0QTWk+dnhqFTgl57Ut
9jm5Wm4Nx2VxkIAJz6tP9xUiTEhITDTqiHJTspoz6PVS6kdiq75M79VzJj1Q9sOaExPTfRX6Bj3V
K9AdMNu78dXrkDJ8kruWHQfxQOh2uqUNyIFx4tgajm5ajthWhVubI7a1IY0jurGx40Hvgu1s4fYn
txt/mJRWs9zpZMmYbZS7042O3Y6nPxNgrt4UH68BG/5AgZibqtKAWxPFTHMrxbljc3eLcw0zlDwD
tRAqgauh7KfwHcWfPv4zd8+ng3xCpihmfrqGe+DTjdwJxFmc4KbEP4BxkgVf8NZtyYI1WdBpgpUm
8CdARQK0KJ9Q0mAWFGUuyVyZyT2ZAU+mw8pU3DShKGVJCtUZs4xUZ8gy0KLEJYnMrKe9J/QJPrce
8vTg14Goa9RRvxYU1ESpAkx4ozHpU7NUmbgDJuhTlapMPpE3IabPQlyVCG3Y0ccnmng+UQVtqfrU
DZkqUyb2bEm5LoWmpJgSspQKVeamVMhKBZIK+lSzxbzJTA3mWvMa807zo+b3zcp3zPNmSsxe86Q5
YlYs9ZrBap41HzBzxNyHbUfNZ8wvmc+aVfqDqmMqqjo9f5vXbkjyteNxSUV4PlufmMKpNmUpTQkK
zqjhSGomx29K55LRRc6nufDWkFaDMAnQN/C47eh14dWKrXjY+BO2Ti5cWkw97t0LF9G4+8yZaFGf
UcufuLCxdXVcSoVEhnlpeDqr0sSWWgZSI8Dy43MrD8KP5677Mi18CC+cVcfhWwfndsPzhy++9tDc
UX+WKGbRjdTL1nyuH+6ToPZil9Suls54PryrbMWzdhGpJF/25m7Jh6w0RxpNFDwCTbbqDD5zckky
1SdDQhKAArjT82e9Zk2SD2916mxtZbOyerYaNlWDtxoQKW82FbCosmgTfQUFa0xgys9f5PBnZ5NK
91qtQVD6NamL/MQoHapZcLFTAt5TpBOpg91RMHm/iTHHko8jZhLAjJyahHMuiCYXzNKKWrgsk6eo
ErlUE7uowE+94/6Smbm5FIPbt2lJQ291ek5lS+emsv2JudVFZf15i6pX7Hv15qXrqrPvaBhwcd9P
XzLQevGWjJKNhsW29KLW4WWeHk+BoAbFnUWNruzM1JnnE1PnchQ0pdTviVjS2VMTtNlJfj9Oo4jc
4TXqbKBWG9INNJHLScmhOafnf+5dotb5iE9lTbNSo7XYWwykeLaY1hiLDxRTb3EfVg4UR4rPFJ8t
Vlml6pliRaau+Z0iKJIuImq9ryjRnydkarX8WrMxyY9Jh9kMr3PsNuLAi53kbmEpYeOlDhP0xl6y
sRdi6TkpB7NzJXMYdh9RxQ87zIAFdC6vMbA0varSlVw06t57/cV9e8AJuKYlN64+83zF6Fe3lg30
bciHC0P71uUpNHr1xTS1+ueK0vSSuUhKuSim2xx/eG/7U7f6dMkZBinXrkabrOaewRvbmLdArbpN
RdUJtyVQtQYgQwlgTkkpKCSF4PEWzhYeLXyp8EIhL93ILEUlvk2FjxbSdeYhMzX7dmj3aKk23W8y
GAsWreUFnDXGGjtJnmc7Lp5QXnA5cb4b2XwxbvLiLoGnEyEtyVZQCmz+qfJxpYpbnelr6y669hvj
FfXXfLV/7WFPlSMvVLNioNGWs+rGgUXN9UvTalLMKdr62SdmZp/YXp2in/v4eGqmc/DIlg1fGKrm
NXoVrvlKnN/vcM0zSSG53isOLd62mB5Wg0a9R03vUcB+BegVoE4mtuY0B3FAMxavY9ZxxsFZHX0S
onCw+WY7Sn1ZvjU88Gn+zNQUv0AK/FqjDW9uazk2WTdb4OiVs/e8Q1rjeEBENwQ8WFmT5OmWcsul
FcbYAPminsTmr6Q/K765e26ne/MDE+4pkeLh5T5omJ7765wlr6Fv6bLNeUXj7lt2Ntmq4JczT97c
qNfpHOVlhg/TSz5+IqMEng8d6C5IM9LfqTWv4tz9OPcmXFu87JFpb8keExxOAV3KvhQqZOVnUU16
Rnph+l3pCnW+z6LTWYpJMXhmi48WXyjmitkJoX6lj0FvWlGpLw98t+H5hPjz8pRWf4ZRuTZJkDw7
OXpfwPt1bJWN52OThvhqpsaWu5Id080AbKlz0edBkVob7s2pq/Nkpq1Y3VUy85XB4heear25v2bu
y9VrxQz4YpLDB68nt9w6vJxXa5XVhiwhwfu5b+/46IPFG+/b1gb3ONddt2rVdeukh1sc6Zpr4l5X
ZJEK0ky6Yb83bUcjrCsfKqflVoxNX3lX+Uj5beWKcjYvDbbQdIx4Fwv9RLXRZ1+MTQWsKYFtmOvU
Bp/Axlmq1Qk+62KkUDUvcpUqbQrS6ctb5M0w+/LYx6K8RXnpuxMhsUn0Zpp9otjqcxB4kuCJ1kSo
hvR09IC3Byp6wNoDPdKxprvPN9sD0z3Q1wOnep7uoVJz1lUdvqM9oOiBWkXPrp5jPdwx7Hu551yP
gvU/tsLnk6C4PAodTgl6U3JyfXEB1NpTJvMrNWT6ajwt5rJ0SFfaXE5FEef3masxP1h8Th93VAc+
nU9X7/cXGev9KdnyitY48VphfN5lPI/JkO3x7NsT6WjlYKck9p1Kb+xCxzay3q1493Cc75VGOjAf
YI5lXuCIvogDdzlMCGBSsm+rVLjD5V7a1NgWUFXKiVX5sVtcWlUa0nAV+bZclh2iLgSuytgVhjVx
Qz94vLA9u5bzVYJw+E5x+5nbtxzaWJRR4rEnO4uy77uvIvD5DdlL3Pmat2z7FuUWNjXPHUy1ZSSm
1fSv3HDzusK5x8Z6Up2rKquuKheEslX05geOa5Q3J+Xsml5xQ2CpzdNWlru0qiJTmVVUtejkytfX
7FhbqFRpuAnHgfypT79d4012VogZ9qVF6bbadbTmhp21vctycpb11tZuqrWwfRX3fe43uO8sJpEn
SAKuhAOdp9BUY6LpJtCwn9RmgxEEY9HRIiBFxqIzRWeLFDVHiy4UUSmVmBxlPmcRGIvAXwSTRbNF
B4o41vGYZZFPInCkCD5iaZ61A7Eb7Vb7GftL9rN2pdqe519MLKlGuz9lUWoOz2e0aVnedsdOxfLX
ySxgWdpmx92txjcxG7lY0OKigZR3OHcse4tVSbgUUm6K1nDngibMOjTbv369vXLDirzw3JYb1nZm
13oqk3fODW6/HVzcR4mLHYsTjHZMrXWbWy8eyigpyaAb27uVap3iYgqr8VT6gh2IgxBlBu5Ty7gn
vbcoRDgnfihSXkwV80ROUQHnKj6soHxFakVeBacrgHcLPimgTxW8WEALrBiVusXw7uJPFtOnFr+4
mC5mLYp8OJf/YT7l81Pz8/I5RR6cy/swj/J5qXl5eZwuDd5N+ySNPpX2YhpNkzgI8K7wiUCfEl7E
OxZrwUPlj706bY4PlEnKXCVnZPvDS7iAXBLeO9X25sLC6vRmZcqhFKpN8TR5tnlooQdMHlB64K/n
PPA/PXDK87SHPuCBgx64yQPTHuj3QAcjEDz5OELxgQee9rzsOefhTnrgmAcqPes8Q8jokIe3e0Dw
gMIDH3rgVc9vPfRpDxzyPO6huzywzQPdHqjwNHhovgeSJbIffxQV97KHOy4JvNUDYQ8MesDvgToP
2D0YV1FSpPyVB172wA894Dk9P+tNe/Skr83T76ENTAUklTSkUt/8sa/5HvCc9NCFLNfJ/KIaHmb6
feThjnmYAtwhD+xiJNskfvmeSg+lnmQPxYn8Njpf+jgjOeihbL7bPFxM4EdMq3Me+kPJGIckczH1
kU0Zk2Ty2D3cyAWZahrFUS9rZ7pwyP4ND0Q8Zzx00LPLc8zD+aNaNng4Y8ySLzEF4GEPHJCUXOrZ
4qHWKGtaLXHt8xz1UFwjL1tKnKK35yBO6pznQ49ili3etCSzwgNZEk9c5zMeoEaP3zPpmfVEPLzB
A2ribp6sBlIN1TX+ZYaUdHuhm6/2FwiVqerc3Oy2BCNxuUraeBaR0pmQfbiliwnLolulINx0+f3z
ytvnwuZNn9Fx2RDH5d+y/T3B3w+We40vb5S+imPPHvAG6yC9DraJb2Ul+nN5DdiWIaR95sYh/JON
JPuqtg5744zZuiGwKb+yq9a2Y67z9tbOzMbG2tSk/XN1+zo7s5cvFZP3z63bvh1SuD62p1TUJBdY
TQt2lq72brU2QVG54lJd2mkyWI2zZpTgeYiddU/iPqPDE9Ht3mW7tAe1lNfCPvXdaqpVwz7F3Qqq
UcAuepBSJQXM+ySX5FpzqTG3LNefezZXwWreXG5pLtuAhRUrfffnwmQueHP7cmdzj+Yq+nJB6krM
K/UJPmWSX2PM8nOC/CzifHTDZc/yjG+fX/A9HZgwr+VLhyNBtSDJsbzHnXz1Vy///OdvvvqLU5nL
B1tW9lULQnXfypbB5ZnwxvvzZO7f//Tpf/w5cFeoqip0V6D/yJaami1Hos8dcudWcRGcby4pIwe8
wZBzh5MqzbAr6WASVSbBLt1BHeV0oMZzvmaRL9HldQFxzbpoDSJ+16TrgOsl1wUXH0W4NS5wCIrs
ZpJrRCu8lKtgDu3PySr1pwhFBWsVGiPxcwYSvR9Kdx6WZ1jG6Y1deaQ5y7NOwcWPOYt0EsgvyOHM
8g05ekWU70KHt4CaptbUrczvur3fXTFyb8i91Y13Hjg2591OBxet2Li0bCy/aMi96xpuKKOkKtmc
qvdc981tU0/c3KTT6S252Zq5dKcznVs9dKCnKMl4MUmteYPlnY759+jP0D4i+YrXvtK110WvT709
lS4RVgrXCnsFBe9Odee5uWWZqzKvz7w9U0FZGkjTJPhy0jV6PPgZU315eSlNpMpaBVVs2cvwFLam
alPVo1VcSVO2TpedUsIX+XMr8hvyaX5+rtHo5yt0DbpjOs6qA52O3ZLc7KQVf/CHhy3pkZ+DPfPD
IxU7QkW/UoDYFZA962NWwcOQMnZ7So3enthDP7xBFHTcstHZs3pJQkm5pb+uN1jUsL5nfUNRaftU
Y8NNy5xFmRvcazuLGruu7mosAnVtqLVQZzDyv7s5e/HaTteKYnNO/rIN9d7BBluK/vmxtHR/Q+nS
whxrofdq6VyDNitR3EgyyHpvDa1WJ/kUSng0C85kQW3WmiyqTWzm/KY+EzWZVIQzclaOU3MKvV/j
1ST6NCqdITVpLZEuTLXuFxzn5Ye3bPboJuHysl4Hj5GQZBNrAa2faksyCex2hPcHWN236bobgrWv
vba0LK/FYihfWmcKD9M7SwpeeaXj4s4VdVrlCq3JoI1+h5yFsf4W9wgxk8Pe7jQv5m69ZpmG6tXL
1FRtUDYbdO/rqElnOWoBYjFazljOWhQ1xGK1lFm8iPNeS59l0hKxKKwSMouEEYuSNEcy4I6M+zPo
mYyXMmiGdFDD20KGKtOvMRuUXJvBJOj8iamxMHCzGbLD8nkpBuSDlhT6eM6SppYkXwRjX5JIu2JN
a2f1NdWfB/f2uT+pzf71XXa2M14DOaBv7zbgDS+j5NMjGSWrjIuyk3PqQq0UHZ/Iz/oV7Lc2EyHL
m7NBu1m7V8ttIJsJ7VQH1bSTC3KUUyoE3OjwkHP2MdzjlDIEPPQ8hn6tYTcfOyJaaAMCrRqtSaPR
UmhTa9TN0a/UKWg0kCMRJick+TQaTqsjWXiO4xYRIx6WznzL1+cjRmhmuDdpcZPvrBFOGZ82vmzk
jhpBahXNi3xGo9VYZuQURjiGnXTWCLTPOGmkao6otRzn1/MGrwZ4TVBD/6IBDVAWMG60pvRVHjhd
0VQpfcOLGcr4wsZeV1LNcqeD+dTffQ3LriIboxlzwZewDHDH53avnLuhDx7/EiSD8ktwNbf505u4
azF3ZF3cTvchjD6XeI//HtrWBG95jVso3rMKS3ybjdcajxg5HXsQlJaY5Gvle3jaz4f5m3juAf4k
/wOe40/Pv+SdQdr9/L083cxfy9MuHrh8E2TQQtpCu6lCSMxPbEpcl6hQagVtvpYTVPkqivuyMboG
BqPJgKsuPdaQ1yD6wKOVPfBI0EObjtc1K/UmpVLPK/SJCRwFQ6UBDGyJtKgVe8BB1ewr3pPZLdI3
vbqklmk9dOqDevbN74Pe7oQWtx6UekFPNbHHIEYi2IUGoUPgjAIoBDglfCjQowI0CNPCLuGgoChj
jzakJwTsYYeCCFDTIZxDKs4rAJ0V4CUBpIcNhcXyw4Ysi+8pASaFWeGowG0SwCqAjiiNSqpM4BKJ
zogW8CerDUAVegPPNsg0t7TYTrcbz0cu6UjDnuSH49/SszvoC65LX8iz35CQnjEmud3Rn6gLvLw7
/TO/nY+mI+lRJfMl3HvRO3QxB8kCd5aE8evmnln9+9+snHtyAp66551fd/zqlSMwxPyEjl48KPvK
LTR48cv0RtlfMuaauL+ivyzibnsCNyQpyjLZiiQgIqTnp7Nv1dUK5h2luiQfLncSJwhp5pyc6Kqb
c0xmc44Abdnm7OY0wZSWhtZUmyHHzJjMa5J8ZnNajoYUElpIvOZcH7F320P2HXau1Q4Z9kJ7jZ3T
2eGv79o/sdO77F+3P2vn9tlhnR2w384e3L9rhyfs8LAddtj32GmPfYudLrdfZadZdoedvmr/rf0j
O/d1O9xth/12uM4OjD0V7IBcf/yJHc6z4c/a6cPRnj2SYI0d/mYH5Py6HZ6L8d8mj3XYl9pb7VyG
HV5F3pJS9Dr7PjvVsN7DOPAN+7t2+qwdTrFBh+zH7VyLHSrtYLLb7VQpj0OdDnlvscO0fZedrrMP
2Sm1wwd2eNl+zk4ft//QTvewTvDb++zUZa+z09jwEWn8SfsP7PSYHb4osxiyQ4cdmuyQbF9kd9k5
hR0+ZKJ+a6en7E/b6XGJdJcd2uz99rCdq7A3MDvk26md3ZT8jT7fD+1wzH7KTmMsGSWV6PKZ8oCy
qz9iGoIkfJf9oP2YnQvbIS7bhYvCNACQmGryFvsk4XYWOJ14tPDbQWKIqr1kBzppn7UfsEfw4s8b
7GvsVC0/JtPrs0maNY160/xpfWkcSTOmUU3acjPozJBcZj7Dnq5YzWVmrsXMOC/y1vt4MzSaO81B
8y1mBQhmzkayc7g0vzXDYFyrV2azRydSFCal4e7LDrAYZ9FfSnO5nL2xK4tjq2PTZ94xLv/9gCt7
r+jZuPBOEm/feDm1/MsE0YvKC45/vO/vlh7UsPuL9JtAGohmWXaMEtjxuhZicS4lgkNzX7DWrR1p
zCxYtCjVmWupcjQtLRMy5470wamDcx/dCRsx4nvW3j68lPJK/rm+tPzGjTU+blKK/gl6pxT50T/G
gKR331tc0r7JsOwvxBL9+4ansgIXGHzh38y3zh26eKc6UfULwv74gcq/mI/jVLlzjWS9esvcobnD
6kT5rzwu/R3BV+h77PcREXuISMMQvsE1kJ0KQvKwdCkfIk3KGrIatpJ12LcBSx22DypuJkNIvxrr
qxDupjWEYPtqLKewbMDSj2Uxlu2MD5bdcn8d0j6AZTPjIZcRbj/ZrNpIxvgfERO/jizF0oH4UsWv
sUxh/UfROspbyZmJI9anMkt9Un+cbp00Zg/252Gd0aap9hOKsITh2N6PfA4znSV+3ydmBZm/gPh2
1MPHfm8AIdN1JUI/ttfKczDhGAetmX8G8QLEC9E2DsSd8txy2RikL0QdO7DfhPUsxg/lUoTJWDKQ
ZxX3Gvk2HCFHGFR0kBpmd+xjdt+BpQ8LZf0IH2DylSbSRUViw/oMsxmro87vc2608yDppEOkAYsD
ae9R3EPquKNELa3LQ+QObK+j10nr2aZE+8uFza1DsvdnFLQrW4cOyf4LCvKrZDbDksz0QloxZv8r
C+r5gIw7rihpuD7MziZm788qKJvB1cz+CwvaVJDX4OdYPpbtHrP/5QXtgrBJXoOFJQNLIoNsrpK8
KyHOncn/h5DNuZisZPNna85sw/T7z6BkF/SlfwKXMrvEoGTnmvlfIMxCeE6yf838vLQGNdJ6S5B/
GHXYQhwsNph/yuMLpMLWDX11IeS8pFmqn5HqDuar8hjnlVDxCsbOvTjmL1Ib03P1lRD9ha0zsw/z
kcIrYDKLRxYTMlx5RZ35WZ4ULwi5LVEo68TiK+u/CuU4p5KPRddXincWc1dC5F+ONP8WW3PZ533y
nJqu1E32+WRpLR4iIpZ3sezBckO0ff6vCF/D4mY8ccxufv/8aeX2+dPcyvnT/I/mn1bunv8u/8H8
07Rg/j9ie53iKPpSHvprNMb6Y/HE1lbCn5fiMbrP5ZHx2F7I9jvFg5JvsX0ujX+deKQ97ndEyX9A
NsvxmaYoxzi6mqxROImVFpAS7iOMAWxTJJNd3J75i9wz5CrWz/lJN6PhXiF9jE6hJgXcL0mlYiU5
zt1HeO4L0r6+WqEl2dwcjnWQVoUfeVfJPO9DHvvn53iK69GAsVow/+9SO45hkLXF9hGlAvcjNm9f
1AfkPaWW+a/yY5KCZSn/J5zXOnneD5EVsl1MisNSfojabQbjmOUBB+YfSgIyjdTPj5GUhfkhZjN5
X8tjPJVtpF3OC0t5N0lVJ5OlrPDHyXKmgyTLR7aqa6Rxaik/JJM+7kfopz6cQ7KUK/z87vm/coVk
iYK1YeGYH8/h+hoxfnzS3rtahrnSvraT5Ej+6UQbsrzA+pTEoiwkNlYUNmLn+5DHcSwTpJH/mNi5
fyXK+F74FvqsT+pbLecaFsMaKfZ/inKflWSZmB6y3AyEdu4IxuOLxBGLkythLG6kvI4Fc8wHarnI
OfIZLKewnGQ46sJiaR0rOI7lyVr6PJnCE8rrWErgDAlynWQCaW9hRfEl8gbGydOwbu4QvUXKZ9ks
56nOkGKEFuXDZAz9b4fqAVzT10ifMo/crHgezyHRnNWJZT2W7WoCDygIGK+ErHAfkgbFb0iJ8hAJ
86fI1dIZYxBj8hS5SvUKHOZ/BJm0fP5L2FYj5YhofyeWDpR1RKq/QhcpXgGef3j+I/5huj9aYvhC
eGWB16N9DLKysO9/t/2/UvBscVmhryAclvBXMCZeIddhUdJXyRgr7OSoehfuw/KFGER7qZHma1hO
YilkBWmn1A44od4CP1V1QpOSwC+wrFV4MQ68ZJniDNooVToLPo3tRlYwtmpZwXV2sXMH7isNCN9E
u2bjGUSBxYklH8si9IHfQANxsYIqFf+n7z5yMP7+MPaGg9Qqvbtol+K/8jp96a1cpVr5d+9z6nH1
25qrNa9qXtVl6iKxd8K5hHOJVye+x96GWw2/MK5LUiRnJ2ebMv/7/d/v/37/9/v/95vd7OlXoI10
kBsIj1d5PHew/1Wg0OENlZOu9tmwLn7/7yM/kHEgRmiUcUpUMCTjHMmC4zKuQJpzMs6TRJoi40pi
oHUyriLX4nkkiqvx3HFexjV4PrPKuA5zfSj+nyZKFTGeCWSC/7OMJxKP8pcoHRQarJ2RNGE4ECvY
ZJySRJxLFOdIJYzLuAJpfiDjPM73LzKuJDl0kYyryIe0TcbVZDH3bzKuQd2ojOtINZ6Do7gezw+3
yngCeZtPkfFEcr1ygNSTCTJJdpAwCZFhMkKmiZUsJgOkEKGLlOG7CrE2EiSDCH0kgBTFiLWQcaQq
RYz9n4VRhJc4TEm1IMIgwm3SWEa5CkfVkUbktgJXuYWsIauxNSTRB7BMI3UAaYNkDGGYbMG2CTL0
T+WT+onJHeHQ8Mi0dfFAodVVVlZlbQsOWn2B6WJry/hAqXXF6KhVIpiyhoNTwfC24GCpdVVLXWPb
io6WNautoSlrwDodDgwGxwLhLdaJocvHE1Q7RPqlqTDhIVRpHBVol1pC7F9XrAr1B8OB6dDEuLU9
GA5hC9N3mMygXdg8SFtweGY0gMgKnOsA9o1LswwjmxLJLv+JgBVTA8HxwWDYWmL9e1n/B+qtkzqn
4sTlaEi20KWkAjuD4SlGW15aVlVa8dn8P5P7P9Xn/26Vo/40LHGZlnhHKUMS706kaJeo/NJIZt9p
Sdq4RNXxGRLXoMQhHM9W4xLlgMR7GutRzhOIj8grtRnXMyxpMCiNi81tinnhAhv/J/6ETjgcmpoO
hrExNG7tLG0vtfoD08HxaWtgfNDaER+4ZmgoNBCUGgeC4ekAEk9Mj6ATbJ4Jh6YGQwNM2lTpZzkV
C+owhvXEZYtwyY3qJ8KTE1F12X9RYRbbJtnhKol8WopdaUj7dHBb0HpVYHo6OMWIR6TuSbIEN2cn
2S69S3HQ5RoMyPJLJWyM/aOVkenpySVO5/bt20sDshoDqEXpwMSY8/+c7TTuXJOSLwQldx5G2qhr
l0o8x9j/gPlnoqd3TAYHg1Oh4XH0+tKR6bHRqANHxU7JbjazwLZRh/hHQdskwegWOHoZH+bODLKx
selOyRMekuREV2sSPyfQ2YKSi5VKrcOSUULouCHEFurH3HRYbrtSm5gul88HXRVtMIXeNyP5ArrU
wk2laWIcN8rRKE2xdSoYtDL7TaEBh4KD6DST4YnNwYHp0onwsHN7aEvIGeUXGh92XmLDuMhyyP/f
2f7fKk9izyLmb0GlP+NFvxL9Gz2gmL15zNQqzMoaosUcrMd8m0gMwJEkkkxSiImkEoGkkXSSQTJJ
FskmZlAQCzpELllEbMRO8kg+KcD8W0iKiANdpgRN4sStuRxzMft/JSKpxG26mtSgKZeSZWQ58ZBa
4sUtoA6DvgFzaxNpxv2zhawkrWiKqzDDrsFdcS3ure24D3bi1r+edJFuPFn1kKtJL9lINuFZKkD+
hewit5DvkkPk9+RW8nmyj9xLvk6Okb3kF+RmcifwoCT7QUVuAzV5GzTkPvIQ+QveYD8iD5BvkGfJ
j8i/4pIMkANopefQ8D8m/4O8SH5CnicvkD/gkv+MvER+Sh7F5btAvkBeJS+TV9Ax3iXnyR5cfrbY
LFbHyVFcxq2SW0xh2E3jvrSd/JFcQ67FSL8OT4bXk9PkK2Qn+RyZJTeS98ifyLdBCzrQQwIkgoFc
JHNghCRIhhQyDwRMkAoCAKRBOmRAJmRBNpghByxghVxYRP5K/gY2sEMe5EMBLIZCKAIHFEMJlIIT
yqAcXORj8hq4oQJEqIQqqIYaWAJLYRksBw/UghdWkF+RX0Md1EMDNEITNIMPWmAltMIquApWwxrw
kwg5AWuhDdqhAzphHayHLuiGDeQT8ik5R34DPXA19MJG2AR9EIB+GIBBCMIQDMMIhGAzbIFRGINx
mIBJ8iRshTBMwTT5LfkdzJDjsA22wzWwA66F6+B6uAE+BzvJz8kvYZa8Qd4kb5Gz5HXyDtwIN8HN
sAtugVthN9wGe2Av7IPbYT98njwId8AB+AJ8Ee6Eg/AlOARfhsNwFxyBu+EeuBfug/vhKHyF3A8P
wL/AMfgqHIevwYPwdXgIHoZH4Bvwr/AoROAEnITHyJfhFHwTHid3w7fgNDwB34Yn4TvwXfgePAVn
4PvwA/g3eBqegR/Cj+DH8Cz8D3gOfgLPwwvwIrwEP4X/CT+Dl+EVeBVeg5/D6/ALeAPehLfgbXgH
zsIv4VfwazgHv4Hfwu/g9/AH+CO8C+/BefgTvA8X4N/hA/gzfAh/gY/gP+Cv8Df4GD6BT+EizME8
ZaFKKUcVlKdKqqJqqqFaqqN6mkATqYEaaRJNpinURFOpQNNoOs2gmTSLZlMzzaEWaqW5dBG1UTvN
o/m0gC6mhbSIOmgxLaGl1EnLyEnyGC2nLvI4+RZ5mrrJKfJN8gy5CW8su8nD5Ie0gorke+QpWkmr
aDWtIf9Bl9CldBldTj20ltxOvXQFraP1tIE20ibaTH20ha6krXQVOUyvIkfIXeR98lXyRbqariH3
kK+RO6ifHCRfomtpG22nHbSTrqPraRftphtoD72a9tKNdBPtowHaTwfoIA3SITpMR2iIbqZb6Cgd
o+N0gk7SrTRMp+g0naHb6HZ6Dd1Br6XX0evpDfRzdCedpTfSm+jNdBe9hd5Kd9Pb6B66l+6jt9P9
5An6eXoHPUC/QL9I76QH6ZfoIfplepjeRY/Qu+k99F56H72fHqVfoQ/Qf6HH6Ffpcfo1+iD9On2I
PkwfUc2Mh8rKVpTJsEGC7qrGaL3OJUO3DEUGXa7yGrleo1oxFhgIT4yrAlGoXNEfxnOLMiAB1YqJ
4Ynx4BZVIAp19QOh8MDM2NBo8BrdwCVcWz84MR0YwI1/WjsQR5UNAwHGcjAKGpB/YFrVKAsMygIb
owKDEtA2XmIUjKOqRlmNYBQqG6McgxLQNS9QaniBUs2XeA3HUX0zHl7GAnJleEFF51vAZ+QSrvD1
B8KKEfxQtkyHRgeDypAEVC3yTELyTFqiMwlFTdci6xyKQtqykoY261YukLH5Eq5vXajVlssqw+Fg
cHwUD7OhAeWqwMDMdFA5KgH9qoV0owsqylVRA41KQLEKZ68YxQ/l6uj48ej41QvHjy8cvzo6fjxq
4PEA+zeV4YnJkSDXOD7MBceHVWvkyU/Ik18TnfyEBBLWjMyMDwfCM2OjgZnphImFNWVbVIdwVIe2
hTqEF+rQFtUhHAXt0VFTEtC1LzDj1AIzdizkNr2QW0eUzXTUIh1sSafZknZGl3QmuqSd8qxm5Fl1
Rmc1IwG+M4zHHX6GfSZ0XjbDmYU1Vae89DNy1KxfoO32BXj3AnzHJVy5ITrXayWg3XDJja+No/zo
xPjwlHYF0yVKFoijqhWNURgIRq21Zmo0MDUSxScu4fr2hdaaWlCRdgdX+QoZ1kVhfQ0/PTE+MZUw
GMI72BRexVhNu2J0ciQgoZrA+MR0cDQYCugbJ6dCqKLUrG6clvtbJmRMv2YsxAwcrXQuINauGQsO
R4mSQkh+mSxekqWoC04H+OYAqquS5Sg2YBOHcviOEcQUTBDfGpicDGDIjPUPBuhVM3T1DO0KqWTJ
1B/i2kYm+PbQ8FiA6wjMqGQtOP9IiKvH4p8K6VsWaGCQCWJ1bSA+cX1w4XSDsemGYtM1zVw+NDoZ
abyin01mmE2GHwyOTgdUMi/FtWxKrHNamhJjxm+RpjQandL4DL0mhAEozYcLj0wop9hkynkJcNM4
J1kuN4nzGcCCVX6CGVi/0LaGK9TTTyxcnZmFqzMRXx3JJyrKyjSBoVCovKzM5Y5hYnkcc8WxS70V
cUyMY5VxrCqOVcexmhhWGZdWWS7Lb4i3xGSVV8T5lse5lce5lce5uS7pHtfYFdfYFdfTFefniuvp
inN2xTm74pzdcc7uOGd3nLM7bgt3XIY7LsMdl+GOy3DHZbjjMiriMiriMiriMiriMiriMi7ZpSIu
oyIuoyIuo+KSveMjKuMjKuMjKuMjKuMjquJaVcV1qYrrUhXXpSrOuSrOuSrOuSrOuSrOuTrOuTo+
3+q4jOq4jOq4jOq4jOq4jOq4jOq4jOq4jJq4jJq4jJq4jJq4jJq4jJq4jJq4jJqqqG+Kl2xxiVtM
Vnk8cvAdx+I+XOaOYxVxTIxjlXGsKo5Vx7EaWX4sNsrL47IuzeGSdjXVyvXD4QDmue1RsD6af7ZL
QLM+ti1otscwZXeUcIcEpDMlipVhdDYsvKoTpC9KMLOEg4P9owlbZybYt3fbsCk4qBwLjUsZPTiA
O48meM0AbmtIFeXibpRPqtETa1lVk2I0FA4oJ4NTbDNsnAlPSGIqy12y4yImL2RluVuUDr6ucgzY
4NQ0HtCmg4MazMVB9m32iH56BM9UUXxKNxTaFsP1U6jcuFzRBMLhie2jwaFplYTNTGolKH0jHu0c
nNg+HsX6J6ZHNDLZ4Lg+jvVPRc3jKqvUToSnR9iJIDCqD41PMyNIX0TqgltnQtsCo8HxgSA/MjEz
FUxAG41ODIcGAqOYULWMGA09Oj0ZR/un1e1NuHT4Yki5jJTFEXcMccWQihhSHUNqYkhlDKmKIaKM
VMT4uGLDxZgIMcbZHePjirW4YjSuGB8xpmpFjNgdU8MVR2LSXTF93HEk1lURE1EeFxrj7IqpWhEn
jnGuiOlTEZ9XjHNFbLgYn2Ccj9SCKbR/dGJgiwrXkkE+WhsdisLwtFyfxkPVYJCXPlWDWySoGQqN
jqLnT1yj9KFxqtxKX3m1WBEFYrk22h1GN1BNh0OB4ZnJKAzL9cHxKBwdUrLT4WhQGojpIzS+rX8G
x04zLNqlnZgMjsuNU2MhdNvAQBD9bFu8wk3NjCuH8No1GlSwD35qEnVUDIzO9PMjwQAKHQwFxjAW
dWMzU7LvBRMX4LHgrKysZ7CprqxchlK0NWHmkKGYGE8bpei35Rjrg3h05SZD5fqhiZnw1MxkMBya
COtZ7MUqCVLwxWtSFMZrAzvCaKzQgHQQN0qH+AXn1aQFeJgduoInNH3fAxUBUit9PgUKbzecvQgv
XgTrRdj5Cfg/gdkPDnxA//1CoeXRC09doGve3/T+o+9zZe+D4X1Qk/PG8/7zfecnzx89r9Qa3gM9
eReSfn222vKO+63Ot91vdpK3YJn/rdm3Im9x7HffN7yl1jW9BVznm5xgMZ6xnik7M3lm9sxLZ86e
uXBGPfu9A9+j3/2O02L4juU71PLYmsd2Psb1PQiGBy0PUv/dfXfTA/eA4R7LPc57uCN3lVruas6x
fPlQgeXsoQuHqPQ3TocSkpo2fQl2fvGOL9LJW2dvPXArN3vLgVvoo9ue2kan/IWWiXGHZby5yJLh
Tu9UublOJTdvYSMb+vMWN/Vt8lo2IVHPhjLLhuZCS4o7uZNHZRVIaOAs0n/QmuDu4J7iVOo2f45l
LZaz/gt+alhjWeNcI/3Pn0BrLjJaOblydiXX0lRo8TVXWwzNlmZn84vN7zS/36zc1Az340/To01P
NXHepkJnk7cpJ7cp25fVKbhTO41uQycF0glu0uk0zBuowbDJsNPA/tCTsD/w4eE0HDjR0e5wtJ5W
zbe1RtT+ngjcFslrZ5/etRsiytsipHNDT9cJgM9337J/P6kzt0Zc7V2RPnN3a2QQES9DZhExmk8I
pK57ampa+r8R4HAgOoOfxDGDTRunoo3EEesmjimYmiJTU+BgfRKKLWTKwZpZCxsDOHLjFGEfrNch
UTFsaip94/8CZeoqowplbmRzdHJlYW0KZW5kb2JqCjE2IDAgb2JqCjE1MTg4CmVuZG9iagoxNyAw
IG9iago8PAovRmlsdGVyIFsgL0ZsYXRlRGVjb2RlIF0KL0xlbmd0aCAxOCAwIFIKPj4Kc3RyZWFt
DQp4nAXBuQmAMAAAwFshNmkUxBmstPUJ2kgCfrj/HN5hdylOjcor+GS3WbI4TDqP1qoX1Qab8Qeu
2gZbCmVuZHN0cmVhbQplbmRvYmoKMTggMCBvYmoKNTgKZW5kb2JqCjE5IDAgb2JqCjw8Ci9DQSAx
Ci9UeXBlIC9FeHRHU3RhdGUKPj4KZW5kb2JqCnhyZWYKMCAyMAowMDAwMDAwMDAwIDY1NTM1IGYN
CjAwMDAwMDAwMTUgMDAwMDAgbg0KMDAwMDAwMDEyMiAwMDAwMCBuDQowMDAwMDAwMTgxIDAwMDAw
IG4NCjAwMDAwMDA1MDMgMDAwMDAgbg0KMDAwMDAwMTIxNiAwMDAwMCBuDQowMDAwMDAxMjM1IDAw
MDAwIG4NCjAwMDAwMDE0ODAgMDAwMDAgbg0KMDAwMDAwMTc3NyAwMDAwMCBuDQowMDAwMDAxNzk2
IDAwMDAwIG4NCjAwMDAwMDIwMDUgMDAwMDAgbg0KMDAwMDAwMjE2MCAwMDAwMCBuDQowMDAwMDAy
NDkyIDAwMDAwIG4NCjAwMDAwMDI5MTMgMDAwMDAgbg0KMDAwMDAwMjkzMyAwMDAwMCBuDQowMDAw
MDAzMTU4IDAwMDAwIG4NCjAwMDAwMTg0NDIgMDAwMDAgbg0KMDAwMDAxODQ2NCAwMDAwMCBuDQow
MDAwMDE4NjAzIDAwMDAwIG4NCjAwMDAwMTg2MjIgMDAwMDAgbg0KdHJhaWxlcgo8PAovSW5mbyAz
IDAgUgovUm9vdCAxIDAgUgovU2l6ZSAyMAo+PgpzdGFydHhyZWYKMTg2NjcKJSVFT0YK

--Apple-Mail=_9331E12B-8BD2-4EC7-B53E-01F3FBEC9227--
"""


MAIL_SINGLE_BINARY = """X-Original-To: raoul@grosbedon.fr
Delivered-To: raoul@grosbedon.fr
Received: by mail1.grosbedon.com (Postfix, from userid 10002)
    id E8166BFACA; Fri, 23 Aug 2013 13:18:01 +0200 (CEST)
From: "Bruce Wayne" <bruce@wayneenterprises.com>
Content-Type: application/pdf;
Content-Disposition: filename=thetruth.pdf
Content-Transfer-Encoding: base64
Message-Id: <6BB1FAB2-2104-438E-9447-07AE2C8C4A92@sexample.com>
Mime-Version: 1.0 (Mac OS X Mail 7.3 \(1878.6\))

SSBhbSB0aGUgQmF0TWFuCg=="""


MAIL_MULTIPART_WEIRD_FILENAME = """X-Original-To: john@doe.com
Delivered-To: johndoe@example.com
Received: by mail.example.com (Postfix, from userid 10002)
    id E8166BFACB; Fri, 23 Aug 2013 13:18:02 +0200 (CEST)
From: "Bruce Wayne" <bruce@wayneenterprises.com>
Subject: test
Message-ID: <c0c20fdd-a38e-b296-865b-d9232bf30ce5@odoo.com>
Date: Mon, 26 Aug 2019 16:55:09 +0200
MIME-Version: 1.0
Content-Type: multipart/mixed;
 boundary="------------FACA7766210AAA981EAE01F3"
Content-Language: en-US

This is a multi-part message in MIME format.
--------------FACA7766210AAA981EAE01F3
Content-Type: text/plain; charset=utf-8; format=flowed
Content-Transfer-Encoding: 7bit

plop


--------------FACA7766210AAA981EAE01F3
Content-Type: text/plain; charset=UTF-8;
 name="=?UTF-8?B?NjJfQDssXVspPS4ow4fDgMOJLnR4dA==?="
Content-Transfer-Encoding: base64
Content-Disposition: attachment;
 filename*0*=utf-8'en-us'%36%32%5F%40%3B%2C%5D%5B%29%3D%2E%28%C3%87%C3%80%C3%89;
 filename*1*=%2E%74%78%74

SSBhbSBhIGZpbGUgd2l0aCBhIHZhbGlkIHdpbmRvd3MgZmlsZW5hbWUK
--------------FACA7766210AAA981EAE01F3--
"""


MAIL_MULTIPART_IMAGE = """X-Original-To: raoul@example.com
Delivered-To: micheline@example.com
Received: by mail1.example.com (Postfix, from userid 99999)
    id 9DFB7BF509; Thu, 17 Dec 2015 15:22:56 +0100 (CET)
X-Spam-Checker-Version: SpamAssassin 3.4.0 (2014-02-07) on mail1.example.com
X-Spam-Level: *
X-Spam-Status: No, score=1.1 required=5.0 tests=FREEMAIL_FROM,
    HTML_IMAGE_ONLY_08,HTML_MESSAGE,RCVD_IN_DNSWL_LOW,RCVD_IN_MSPIKE_H3,
    RCVD_IN_MSPIKE_WL,T_DKIM_INVALID autolearn=no autolearn_force=no version=3.4.0
Received: from mail-lf0-f44.example.com (mail-lf0-f44.example.com [209.85.215.44])
    by mail1.example.com (Postfix) with ESMTPS id 1D80DBF509
    for <micheline@example.com>; Thu, 17 Dec 2015 15:22:56 +0100 (CET)
Authentication-Results: mail1.example.com; dkim=pass
    reason="2048-bit key; unprotected key"
    header.d=example.com header.i=@example.com header.b=kUkTIIlt;
    dkim-adsp=pass; dkim-atps=neutral
Received: by mail-lf0-f44.example.com with SMTP id z124so47959461lfa.3
        for <micheline@example.com>; Thu, 17 Dec 2015 06:22:56 -0800 (PST)
DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed;
        d=example.com; s=20120113;
        h=mime-version:date:message-id:subject:from:to:content-type;
        bh=GdrEuMrz6vxo/Z/F+mJVho/1wSe6hbxLx2SsP8tihzw=;
        b=kUkTIIlt6fe4dftKHPNBkdHU2rO052o684R0e2bqH7roGUQFb78scYE+kqX0wo1zlk
         zhKPVBR1TqTsYlqcHu+D3aUzai7L/Q5m40sSGn7uYGkZJ6m1TwrWNqVIgTZibarqvy94
         NWhrjjK9gqd8segQdSjCgTipNSZME4bJCzPyBg/D5mqe07FPBJBGoF9SmIzEBhYeqLj1
         GrXjb/D8J11aOyzmVvyt+bT+oeLUJI8E7qO5g2eQkMncyu+TyIXaRofOOBA14NhQ+0nS
         w5O9rzzqkKuJEG4U2TJ2Vi2nl2tHJW2QPfTtFgcCzGxQ0+5n88OVlbGTLnhEIJ/SYpem
         O5EA==
MIME-Version: 1.0
X-Received: by 10.25.167.197 with SMTP id q188mr22222517lfe.129.1450362175493;
 Thu, 17 Dec 2015 06:22:55 -0800 (PST)
Received: by 10.25.209.145 with HTTP; Thu, 17 Dec 2015 06:22:55 -0800 (PST)
Date: Thu, 17 Dec 2015 15:22:55 +0100
Message-ID: <CAP76m_UB=aLqWEFccnq86AhkpwRB3aZoGL9vMffX7co3YEro_A@mail.gmail.com>
Subject: {subject}
From: =?UTF-8?Q?Thibault_Delavall=C3=A9e?= <raoul@example.com>
To: {to}
Content-Type: multipart/related; boundary=001a11416b9e9b229a05272b7052

--001a11416b9e9b229a05272b7052
Content-Type: multipart/alternative; boundary=001a11416b9e9b229805272b7051

--001a11416b9e9b229805272b7051
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: quoted-printable

Premi=C3=A8re image, orang=C3=A9e.

[image: Inline image 1]

Seconde image, rosa=C3=A7=C3=A9e.

[image: Inline image 2]

Troisi=C3=A8me image, verte!=C2=B5

[image: Inline image 3]

J'esp=C3=A8re que tout se passera bien.
--=20
Thibault Delavall=C3=A9e

--001a11416b9e9b229805272b7051
Content-Type: text/html; charset=UTF-8
Content-Transfer-Encoding: quoted-printable

<div dir=3D"ltr"><div>Premi=C3=A8re image, orang=C3=A9e.</div><div><br></di=
v><div><img src=3D"cid:ii_151b519fc025fdd3" alt=3D"Inline image 1" width=3D=
"2" height=3D"2"><br></div><div><br></div><div>Seconde image, rosa=C3=A7=C3=
=A9e.</div><div><br></div><div><img src=3D"cid:ii_151b51a290ed6a91" alt=3D"=
Inline image 2" width=3D"2" height=3D"2"></div><div><br></div><div>Troisi=
=C3=A8me image, verte!=C2=B5</div><div><br></div><div><img src=3D"cid:ii_15=
1b51a37e5eb7a6" alt=3D"Inline image 3" width=3D"10" height=3D"10"><br></div=
><div><br></div><div>J&#39;esp=C3=A8re que tout se passera bien.</div>-- <b=
r><div class=3D"gmail_signature">Thibault Delavall=C3=A9e</div>
</div>

--001a11416b9e9b229805272b7051--
--001a11416b9e9b229a05272b7052
Content-Type: image/gif; name="=?UTF-8?B?b3JhbmfDqWUuZ2lm?="
Content-Disposition: inline; filename="=?UTF-8?B?b3JhbmfDqWUuZ2lm?="
Content-Transfer-Encoding: base64
Content-ID: <ii_151b519fc025fdd3>
X-Attachment-Id: ii_151b519fc025fdd3

R0lGODdhAgACALMAAAAAAP///wAAAP//AP8AAP+AAAD/AAAAAAAA//8A/wAAAAAAAAAAAAAAAAAA
AAAAACwAAAAAAgACAAAEA7DIEgA7
--001a11416b9e9b229a05272b7052
Content-Type: image/gif; name="=?UTF-8?B?dmVydGUhwrUuZ2lm?="
Content-Disposition: inline; filename="=?UTF-8?B?dmVydGUhwrUuZ2lm?="
Content-Transfer-Encoding: base64
Content-ID: <ii_151b51a37e5eb7a6>
X-Attachment-Id: ii_151b51a37e5eb7a6

R0lGODlhCgAKALMAAAAAAIAAAACAAICAAAAAgIAAgACAgMDAwICAgP8AAAD/AP//AAAA//8A/wD/
/////ywAAAAACgAKAAAEClDJSau9OOvNe44AOw==
--001a11416b9e9b229a05272b7052
Content-Type: image/gif; name="=?UTF-8?B?cm9zYcOnw6llLmdpZg==?="
Content-Disposition: inline; filename="=?UTF-8?B?cm9zYcOnw6llLmdpZg==?="
Content-Transfer-Encoding: base64
Content-ID: <ii_151b51a290ed6a91>
X-Attachment-Id: ii_151b51a290ed6a91

R0lGODdhAgACALMAAAAAAP///wAAAP//AP8AAP+AAAD/AAAAAAAA//8A/wAAAP+AgAAAAAAAAAAA
AAAAACwAAAAAAgACAAAEA3DJFQA7
--001a11416b9e9b229a05272b7052--
"""

MAIL_EML_ATTACHMENT = """Subject: Re: test attac
From: {email_from}
To: {to}
References: <f3b9f8f8-28fa-2543-cab2-7aa68f679ebb@odoo.com>
Message-ID: <cb7eaf62-58dc-2017-148c-305d0c78892f@odoo.com>
Date: Wed, 14 Mar 2018 14:26:58 +0100
User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101
 Thunderbird/52.6.0
MIME-Version: 1.0
In-Reply-To: <f3b9f8f8-28fa-2543-cab2-7aa68f679ebb@odoo.com>
Content-Type: multipart/mixed;
 boundary="------------A6B5FD5F68F4D73ECD739009"
Content-Language: en-US

This is a multi-part message in MIME format.
--------------A6B5FD5F68F4D73ECD739009
Content-Type: text/plain; charset=utf-8; format=flowed
Content-Transfer-Encoding: 7bit



On 14/03/18 14:20, Anon wrote:
> Some nice content
>


--------------A6B5FD5F68F4D73ECD739009
Content-Type: message/rfc822;
 name="original_msg.eml"
Content-Transfer-Encoding: 8bit
Content-Disposition: attachment;
 filename="original_msg.eml"

Delivered-To: anon2@gmail1.openerp.com
Received: by 10.46.1.170 with SMTP id f42csp2379722lji;
        Mon, 5 Mar 2018 01:19:23 -0800 (PST)
X-Google-Smtp-Source: AG47ELsYTlAcblMxfnaEENQuF+MFoac5Q07wieyw0cybq/qOX4+DmayqoQILkiWT+NiTOcnr/ACO
X-Received: by 10.28.154.213 with SMTP id c204mr7237750wme.64.1520241563503;
        Mon, 05 Mar 2018 01:19:23 -0800 (PST)
ARC-Seal: i=1; a=rsa-sha256; t=1520241563; cv=none;
        d=google.com; s=arc-20160816;
        b=BqgMSbqmbpYW1ZtfGTVjj/654MBmabw4XadNZEaI96hDaub6N6cP8Guu3PoxscI9os
         0OLYVP1s/B+Vv9rIzulCwHyHsgnX+aTxGYepTDN6x8SA9Qeb9aQoNSVvQLryTAoGpaFr
         vXhw8aPWyr28edE03TDFA/s7X65Bf6dV5zJdMiUPVqGkfYfcTHMf3nDER5vk8vQj7tve
         Cfyy0h9vLU9RSEtdFwmlEkLmgT9NQ3GDf0jQ97eMXPgR2q6duCPoMcz15KlWOno53xgH
         EiV7aIZ5ZMN/m+/2xt3br/ubJ5euFojWhDnHUZoaqd08TCSQPd4fFCCx75MjDeCnwYMn
         iKSg==
ARC-Message-Signature: i=1; a=rsa-sha256; c=relaxed/relaxed; d=google.com; s=arc-20160816;
        h=content-language:mime-version:user-agent:date:message-id:subject
         :from:to:dkim-signature:arc-authentication-results;
        bh=/UIFqhjCCbwBLsI4w7YY98QH6G/wxe+2W4bbMDCskjM=;
        b=Wv5jt+usnSgWI96GaZWUN8/VKl1drueDpU/4gkyX/iK4d6S4CuSDjwYAc3guz/TjeW
         GoKCqT30IGZoStpXQbuLry7ezXNK+Fp8MJKN2n/x5ClJWHxIsxIGlP2QC3TO8RI0P5o0
         GXG9izW93q1ubkdPJFt3unSjjwSYf5XVQAZQtRm9xKjqA+lbtFbsnbjJ4wgYBURnD8ma
         Qxb2xsxXDelaZvtdlzHRDn5SEkbqhcCclEYw6oRLpVQFZeYtPxcCleVybtj2owJxdaLp
         7wXuo/gpYe6E2cPuS2opei8AzjEhYTNzlYXTPvaoxCCTTjfGTaPv22TeRDehuIXngSEl
         Nmmw==
ARC-Authentication-Results: i=1; mx.google.com;
       dkim=pass header.i=@odoo.com header.s=mail header.b=MCzhjB9b;
       spf=pass (google.com: domain of soup@odoo.com designates 149.202.180.44 as permitted sender) smtp.mailfrom=soup@odoo.com;
       dmarc=pass (p=NONE sp=NONE dis=NONE) header.from=odoo.com
Return-Path: <soup@odoo.com>
Received: from mail2.odoo.com (mail2.odoo.com. [149.202.180.44])
        by mx.google.com with ESMTPS id y4si4279200wmy.148.2018.03.05.01.19.22
        (version=TLS1_2 cipher=ECDHE-RSA-AES128-GCM-SHA256 bits=128/128);
        Mon, 05 Mar 2018 01:19:23 -0800 (PST)
Received-SPF: pass (google.com: domain of soup@odoo.com designates 149.202.180.44 as permitted sender) client-ip=149.202.180.44;
Authentication-Results: mx.google.com;
       dkim=pass header.i=@odoo.com header.s=mail header.b=MCzhjB9b;
       spf=pass (google.com: domain of soup@odoo.com designates 149.202.180.44 as permitted sender) smtp.mailfrom=soup@odoo.com;
       dmarc=pass (p=NONE sp=NONE dis=NONE) header.from=odoo.com
Received: from [10.10.31.24] (unknown [91.183.114.50])
	(Authenticated sender: soup)
	by mail2.odoo.com (Postfix) with ESMTPSA id 7B571A4085
	for <what@odoo.com>; Mon,  5 Mar 2018 10:19:21 +0100 (CET)
DKIM-Signature: v=1; a=rsa-sha256; c=simple/simple; d=odoo.com; s=mail;
	t=1520241562; bh=L2r7Sp/vjogIdM1k8H9zDGDjnhKolsTTLLjndnFC4Jc=;
	h=To:From:Subject:Date:From;
	b=MCzhjB9bnsrJ3uKjq+GjujFxmtrq3fc7Vv7Vg2C72EPKnkxgqy6yPjWKtXbBlaiT3
	 YjKI24aiSQlOeOPQiqFgiDzeqqemNDp+CRuhoYz1Vbz+ESRaHtkWRLb7ZjvohS2k7e
	 RTq7tUxY2nUL2YrNHV7DFYtJVBwiTuyLP6eAiJdE=
To: what@odoo.com
From: Soup <soup@odoo.com>
Subject: =?UTF-8?Q?Soupe_du_jour_:_Pois_cass=c3=a9s?=
Message-ID: <a05d8334-7b7c-df68-c96a-4a88ed19f31b@odoo.com>
Date: Mon, 5 Mar 2018 10:19:21 +0100
User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101
 Thunderbird/52.6.0
MIME-Version: 1.0
Content-Type: multipart/alternative;
 boundary="------------1F2D18B1129FC2F0B9EECF50"
Content-Language: en-US
X-Spam-Status: No, score=-1.2 required=5.0 tests=ALL_TRUSTED,BAYES_00,
	HTML_IMAGE_ONLY_08,HTML_MESSAGE,T_REMOTE_IMAGE autolearn=no
	autolearn_force=no version=3.4.0
X-Spam-Checker-Version: SpamAssassin 3.4.0 (2014-02-07) on mail2.odoo.com

This is a multi-part message in MIME format.
--------------1F2D18B1129FC2F0B9EECF50
Content-Type: text/plain; charset=utf-8; format=flowed
Content-Transfer-Encoding: 8bit

Résultat de recherche d'images pour "dessin la princesse au petit pois"

--
Soup

Odoo S.A.
Chaussée de Namur, 40
B-1367 Grand Rosière
Web: http://www.odoo.com


--------------1F2D18B1129FC2F0B9EECF50
Content-Type: text/html; charset=utf-8
Content-Transfer-Encoding: 8bit

<html>
  <head>

    <meta http-equiv="content-type" content="text/html; charset=utf-8">
  </head>
  <body text="#000000" bgcolor="#FFFFFF">
    <p><img
src="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQjCNAadd3NDM8g9w0P_-gAVYrrqC0wmBNYKGsTZ2Pst5SsNxTRnA"
        alt="Résultat de recherche d'images pour &quot;dessin la
        princesse au petit pois&quot;"></p>
    <pre class="moz-signature" cols="72">--
Soup

Odoo S.A.
Chaussée de Namur, 40
B-1367 Grand Rosière
Web: <a class="moz-txt-link-freetext" href="http://www.odoo.com">http://www.odoo.com</a> </pre>
  </body>
</html>

--------------1F2D18B1129FC2F0B9EECF50--

--------------A6B5FD5F68F4D73ECD739009--"""

MAIL_EML_ATTACHMENT_BOUNCE_HEADERS="""\
Date: Tue, 24 Dec 2019 11:32:07 +0100 (CET)
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary=16063919151.b32bE0eD.7
Content-Transfer-Encoding: 7bit
Subject: Undelivered Mail Returned to Sender
From: {email_from}
To: {to}
Message-Id: <20191224103207.415713014C@example.com>
Return-Path: <MAILER-DAEMON>
Delivered-To: odoo+82240-account.invoice-19177@mycompany.example.com
Received: by example.com (Postfix) id 415713014C; Tue, 24 Dec
 2019 11:32:07 +0100 (CET)
Auto-Submitted: auto-replied


--16063919151.b32bE0eD.7
MIME-Version: 1.0
Content-Type: multipart/alternative; boundary=16063919150.2cD3F37.7
Content-Transfer-Encoding: 7bit
Content-ID: <16063919152.fD96.7@8f286b7b7880>


--16063919150.2cD3F37.7
Content-Type: text/plain; charset=US-ASCII
Content-Disposition: inline
Content-Transfer-Encoding: 8bit

This is the mail system at host example.com.

I'm sorry to have to inform you that your message could not
be delivered to one or more recipients. It's attached below.

For further assistance, please send mail to postmaster.

If you do so, please include this problem report. You can
delete your own text from the attached returned message.


--16063919151.b32bE0eD.7
Content-Type: text/rfc822-headers
Content-Transfer-Encoding: 7bit

Return-Path: <bounce+82240-account.invoice-19177@mycompany.example.com>
Received: by example.com (Postfix) id 415713014C; Tue, 24 Dec
Content-Type: multipart/mixed; boundary="===============3600759226158551994=="
MIME-Version: 1.0
Message-Id: {msg_id}
references: <1571814481.189281940460205.799582441238467-openerp-19177-account.invoice@mycompany.example.com>
Subject: Test
From: "Test" <noreply+srglvrz-gmail.com@mycompany.example.com>
Reply-To: "MY COMPANY" <info@mycompany.example.com>
To: "Test" <test@anothercompany.example.com>
Date: Tue, 24 Dec 2019 10:32:05 -0000
X-Odoo-Objects: account.invoice-19177

--16063919151.b32bE0eD.7--"""

MAIL_XHTML = """Return-Path: <xxxx@xxxx.com>
Received: from xxxx.internal (xxxx.xxxx.internal [1.1.1.1])
	 by xxxx (xxxx 1.1.1-111-g972eecc-slipenbois) with LMTPA;
	 Fri, 13 Apr 2018 22:11:52 -0400
X-Cyrus-Session-Id: sloti35d1t38-1111111-11111111111-5-11111111111111111111
X-Sieve: CMU Sieve 1.0
X-Spam-known-sender: no ("Email failed DMARC policy for domain"); in-addressbook
X-Spam-score: 0.0
X-Spam-hits: ALL_TRUSTED -1, BAYES_00 -1.9, FREEMAIL_FROM 0.001,
  HTML_FONT_LOW_CONTRAST 0.001, HTML_MESSAGE 0.001, SPF_SOFTFAIL 0.665,
  LANGUAGES en, BAYES_USED global, SA_VERSION 1.1.0
X-Spam-source: IP='1.1.1.1', Host='unk', Country='unk', FromHeader='com',
  MailFrom='com'
X-Spam-charsets: plain='utf-8', html='utf-8'
X-IgnoreVacation: yes ("Email failed DMARC policy for domain")
X-Resolved-to: catchall@xxxx.xxxx
X-Delivered-to: catchall@xxxx.xxxx
X-Mail-from: xxxx@xxxx.com
Received: from mx4 ([1.1.1.1])
  by xxxx.internal (LMTPProxy); Fri, 13 Apr 2018 22:11:52 -0400
Received: from xxxx.xxxx.com (localhost [127.0.0.1])
	by xxxx.xxxx.internal (Postfix) with ESMTP id E1111C1111;
	Fri, 13 Apr 2018 22:11:51 -0400 (EDT)
Received: from xxxx.xxxx.internal (localhost [127.0.0.1])
    by xxxx.xxxx.com (Authentication Milter) with ESMTP
    id BBDD1111D1A;
    Fri, 13 Apr 2018 22:11:51 -0400
ARC-Authentication-Results: i=1; xxxx.xxxx.com; arc=none (no signatures found);
    dkim=pass (2048-bit rsa key sha256) header.d=xxxx.com header.i=@xxxx.com header.b=P1aaAAaa x-bits=2048 x-keytype=rsa x-algorithm=sha256 x-selector=fm2;
    dmarc=fail (p=none,d=none) header.from=xxxx.com;
    iprev=pass policy.iprev=1.1.1.1 (out1-smtp.xxxx.com);
    spf=softfail smtp.mailfrom=xxxx@xxxx.com smtp.helo=out1-smtp.xxxx.com;
    x-aligned-from=pass (Address match);
    x-cm=none score=0;
    x-ptr=pass x-ptr-helo=out1-smtp.xxxx.com x-ptr-lookup=out1-smtp.xxxx.com;
    x-return-mx=pass smtp.domain=xxxx.com smtp.result=pass smtp_is_org_domain=yes header.domain=xxxx.com header.result=pass header_is_org_domain=yes;
    x-tls=pass version=TLSv1.2 cipher=ECDHE-RSA-AES128-GCM-SHA256 bits=128/128;
    x-vs=clean score=0 state=0
Authentication-Results: xxxx.xxxx.com;
    arc=none (no signatures found);
    dkim=pass (2048-bit rsa key sha256) header.d=xxxx.com header.i=@xxxx.com header.b=P1awJPiy x-bits=2048 x-keytype=rsa x-algorithm=sha256 x-selector=fm2;
    dmarc=fail (p=none,d=none) header.from=xxxx.com;
    iprev=pass policy.iprev=66.111.4.25 (out1-smtp.xxxx.com);
    spf=softfail smtp.mailfrom=xxxx@xxxx.com smtp.helo=out1-smtp.xxxx.com;
    x-aligned-from=pass (Address match);
    x-cm=none score=0;
    x-ptr=pass x-ptr-helo=out1-smtp.xxxx.com x-ptr-lookup=out1-smtp.xxxx.com;
    x-return-mx=pass smtp.domain=xxxx.com smtp.result=pass smtp_is_org_domain=yes header.domain=xxxx.com header.result=pass header_is_org_domain=yes;
    x-tls=pass version=TLSv1.2 cipher=ECDHE-RSA-AES128-GCM-SHA256 bits=128/128;
    x-vs=clean score=0 state=0
X-ME-VSCategory: clean
X-ME-CMScore: 0
X-ME-CMCategory: none
Received-SPF: softfail
    (gmail.com ... _spf.xxxx.com: Sender is not authorized by default to use 'xxxx@xxxx.com' in 'mfrom' identity, however domain is not currently prepared for false failures (mechanism '~all' matched))
    receiver=xxxx.xxxx.com;
    identity=mailfrom;
    envelope-from="xxxx@xxxx.com";
    helo=out1-smtp.xxxx.com;
    client-ip=1.1.1.1
Received: from xxxx.xxxx.internal (gateway1.xxxx.internal [1.1.1.1])
	(using TLSv1.2 with cipher ECDHE-RSA-AES128-GCM-SHA256 (128/128 bits))
	(No client certificate requested)
	by xxxx.xxxx.internal (Postfix) with ESMTPS;
	Fri, 13 Apr 2018 22:11:51 -0400 (EDT)
Received: from compute3.internal (xxxx.xxxx.internal [10.202.2.43])
	by xxxx.xxxx.internal (Postfix) with ESMTP id 8BD5B21BBD;
	Fri, 13 Apr 2018 22:11:51 -0400 (EDT)
Received: from xxxx ([10.202.2.163])
  by xxxx.internal (MEProxy); Fri, 13 Apr 2018 22:11:51 -0400
X-ME-Sender: <xms:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa>
Received: from [1.1.1.1] (unknown [1.1.1.1])
	by mail.xxxx.com (Postfix) with ESMTPA id BF5E1111D
	for <catchall@xxxx.xxxx>; Fri, 13 Apr 2018 22:11:50 -0400 (EDT)
From: Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>
To: generic@mydomain.com
Subject: Re: xxxx (Ref PO1)
Date: Sat, 14 Apr 2018 02:11:42 +0000
Message-Id: <em67f5c44a-xxxx-xxxx-xxxx-69f56d618a94@wswin7hg4n4l1ce>
In-Reply-To: <829228111124527.1111111602.256611118262939-openerp-129-xxxx.xxxx@ip-1-1-1-1>
References: <867911111953277.1523671337.187951111160400-openerp-129-xxxx.xxxx@ip-1-1-1-1>
 <867911111953277.1523671337.256611118262939-openerp-129-xxxx.xxxx@ip-1-1-1-1>
Reply-To: "xxxx xxxx" <xxxx@xxxx.com>
User-Agent: eM_Client/7.0.26687.0
Mime-Version: 1.0
Content-Type: multipart/alternative;
 boundary="------=_MB48E455BD-1111-42EC-1111-886CDF48905E"

--------=_MB48E455BD-1111-42EC-1111-886CDF48905E
Content-Type: text/plain; format=flowed; charset=utf-8
Content-Transfer-Encoding: quoted-printable

xxxx


------ Original Message ------
From: "xxxx" <xxxx@xxxx.com>
To: "xxxx" <xxxx@xxxx.com>
Sent: 4/13/2018 7:06:43 PM
Subject: xxxx

>xxxx

--------=_MB48E455BD-1111-42EC-1111-886CDF48905E
Content-Type: text/html; charset=utf-8
Content-Transfer-Encoding: quoted-printable

<?xml version=3D"1.0" encoding=3D"utf-16"?><html><head><style type=3D"text/=
css"><!--blockquote.cite
{margin-left: 5px; margin-right: 0px; padding-left: 10px; padding-right:=
 0px; border-left-width: 1px; border-left-style: solid; border-left-color:=
 rgb(204, 204, 204);}
blockquote.cite2
{margin-left: 5px; margin-right: 0px; padding-left: 10px; padding-right:=
 0px; border-left-width: 1px; border-left-style: solid; border-left-color:=
 rgb(204, 204, 204); margin-top: 3px; padding-top: 0px;}
a img
{border: 0px;}
body
{font-family: Tahoma; font-size: 12pt;}
--></style></head><body><div>this is a reply to PO200109 from emClient</div=
><div id=3D"signature_old"><div style=3D"font-family: Tahoma; font-size:=
 12 pt;">-- <br /><span><span class=3D"__postbox-detected-content __postbox=
-detected-address" style=3D"TEXT-DECORATION: underline; COLOR: rgb(115,133,=
172); PADDING-BOTTOM: 0pt; PADDING-TOP: 0pt; PADDING-LEFT: 0pt; DISPLAY:=
 inline; PADDING-RIGHT: 0pt" __postbox-detected-content=3D"__postbox-detect=
ed-address"></span>xxxx<br />xxxx<br /><b=
r />xxxx</span></=
div></div><div><br /></div><div><br /></div><div><br /></div>
<div>------ Original Message ------</div>
<div>From: "xxxx" &lt;<a href=3D"mailto:xxxx@xxxx.com">xxxx=
@xxxx.com</a>&gt;</div>
<div>To: "xxxx" &lt;<a href=3D"mailto:xxxx@xxxx.com">a=
xxxx@xxxx.com</a>&gt;</div>
<div>Sent: 4/13/2018 7:06:43 PM</div>
<div>Subject: xxxx</div><div><br /></div=
>
<div id=3D"x00b4101ba6e64ce"><blockquote cite=3D"829228972724527.1523671602=
.256660938262939-openerp-129-xxxx.xxxx@ip-1-1-1-1" type=3D"cite"=
 class=3D"cite2">
<table border=3D"0" width=3D"100%" cellpadding=3D"0" bgcolor=3D"#ededed"=
 style=3D"padding: 20px; background-color: #ededed" summary=3D"o_mail_notif=
ication">
                    <tbody>

                      <!-- HEADER -->
                      <tr>
                        <td align=3D"center" style=3D"min-width: 590px;">
                          <table width=3D"590" border=3D"0" cellpadding=3D=
"0" bgcolor=3D"#875A7B" style=3D"min-width: 590px; background-color: rgb(13=
5,90,123); padding: 20px;">
                            <tbody><tr>
                              <td valign=3D"middle">
                                  <span style=3D"font-size:20px; color:whit=
e; font-weight: bold;">
                                      mangez des saucisses
                                  </span>
                              </td>
                              <td valign=3D"middle" align=3D"right">
                                  <img src=3D"http://erp.xxxx.xxxx/logo.png=
" style=3D"padding: 0px; margin: 0px; height: auto; width: 80px;" alt=3D=
"xxxx" />
                              </td>
                            </tr>
                          </tbody></table>
                        </td>
                      </tr>

                      <!-- CONTENT -->
                      <tr>
                        <td align=3D"center" style=3D"min-width: 590px;">
                          <table width=3D"590" border=3D"0" cellpadding=3D=
"0" bgcolor=3D"#ffffff" style=3D"min-width: 590px; background-color: rgb(25=
5, 255, 255); padding: 20px;">
                            <tbody>
                              <tr><td valign=3D"top" style=3D"font-family:A=
rial,Helvetica,sans-serif; color: #555; font-size: 14px;">
                                <p style=3D"margin: 0px 0px 9px 0px; font-s=
ize: 13px; font-family: &quot;Lucida Grande&quot;, Helvetica, Verdana, Aria=
l, sans-serif">xxxx.=20
,</p>
<p style=3D"margin: 0px 0px 9px 0px; font-size: 13px; font-family: &quot;Lu=
cida Grande&quot;, Helvetica, Verdana, Arial, sans-serif">
xxxx.
</p>

<p style=3D"margin: 0px 0px 9px 0px; font-size: 13px; font-family: &quot;Lu=
cida Grande&quot;, Helvetica, Verdana, Arial, sans-serif">You can reply =
to this email if you have any questions.</p>
<p style=3D"margin: 0px 0px 9px 0px; font-size: 13px; font-family: &quot;Lu=
cida Grande&quot;, Helvetica, Verdana, Arial, sans-serif">Thank you,</p>
                              </td>
                            </tr></tbody>
                          </table>
                        </td>
                      </tr>

                      <!-- FOOTER -->
                      <tr>
                        <td align=3D"center" style=3D"min-width: 590px;">
                          <table width=3D"590" border=3D"0" cellpadding=3D=
"0" bgcolor=3D"#875A7B" style=3D"min-width: 590px; background-color: rgb(13=
5,90,123); padding: 20px;">
                            <tbody><tr>
                              <td valign=3D"middle" align=3D"left" style=
=3D"color: #fff; padding-top: 10px; padding-bottom: 10px; font-size: 12px;"=
>
                                xxxx<br />
                                +1-801-980-4240
                              </td>
                              <td valign=3D"middle" align=3D"right" style=
=3D"color: #fff; padding-top: 10px; padding-bottom: 10px; font-size: 12px;"=
>
                                <a href=3D"http://erp.xxxx.xxxx/info@xxxx-a=
aa.com" style=3D"text-decoration:none; color: white;">info@aust-mfg.com</a>=
<br />
                                    <a href=3D"http://www.xxxx=
.com" style=3D"text-decoration:none; color: white;">
                                        http://www.xxxx.com
                                    </a>
                              </td>
                            </tr>
                          </tbody></table>
                        </td>
                      </tr>
                      <tr>
                        <td align=3D"center">
                            Powered by <a href=3D"https://www.odoo.com">Odo=
o</a>.
                        </td>
                      </tr>
                    </tbody>
                </table>
               =20
                <pre style=3D"white-space: pre-wrap">xxxx.
</pre>
</blockquote></div>
</body></html>
--------=_MB48E455BD-2850-42EC-B1CA-886CDF48905E--"""


MAIL_BOUNCE = """Return-Path: <>
X-Original-To: {to}
Delivered-To: {to}
Received: by mail2.test.ironsky (Postfix)
    id 93A83A5F0D; Mon, 15 Apr 2019 15:41:06 +0200 (CEST)
Date: Mon, 15 Apr 2019 15:41:06 +0200 (CEST)
From: MAILER-DAEMON@mail2.test.ironsky (Mail Delivery System)
Subject: {subject}
To: {to}
Auto-Submitted: auto-replied
MIME-Version: 1.0
Content-Type: multipart/report; report-type=delivery-status;
    boundary="92726A5F09.1555335666/mail2.test.ironsky"
Message-Id: <20190415134106.93A83A5F0D@mail2.test.ironsky>

This is a MIME-encapsulated message.

--92726A5F09.1555335666/mail2.test.ironsky
Content-Description: Notification
Content-Type: text/plain; charset=us-ascii

This is the mail system at host mail2.test.ironsky.

I'm sorry to have to inform you that your message could not
be delivered to one or more recipients. It's attached below.

For further assistance, please send mail to postmaster.

If you do so, please include this problem report. You can
delete your own text from the attached returned message.

                   The mail system

<{email_from}>: host tribulant.com[23.22.38.89] said: 550 No such
    person at this address. (in reply to RCPT TO command)

--92726A5F09.1555335666/mail2.test.ironsky
Content-Description: Delivery report
Content-Type: message/delivery-status

Reporting-MTA: dns; mail2.test.ironsky
X-Postfix-Queue-ID: 92726A5F09
X-Postfix-Sender: rfc822; {to}
Arrival-Date: Mon, 15 Apr 2019 15:40:24 +0200 (CEST)

Final-Recipient: rfc822; {email_from}
Original-Recipient: rfc822;{email_from}
Action: failed
Status: 5.0.0
Remote-MTA: dns; tribulant.com
Diagnostic-Code: smtp; 550 No such person at this address.

--92726A5F09.1555335666/mail2.test.ironsky
Content-Description: Undelivered Message
Content-Type: message/rfc822

Return-Path: <{to}>
Received: from [127.0.0.1] (host-212-68-194-133.dynamic.voo.be [212.68.194.133])
    (Authenticated sender: aaa)
    by mail2.test.ironsky (Postfix) with ESMTPSA id 92726A5F09
    for <{email_from}>; Mon, 15 Apr 2019 15:40:24 +0200 (CEST)
DKIM-Signature: v=1; a=rsa-sha256; c=simple/simple; d=test.ironsky; s=mail;
    t=1555335624; bh=x6cSjphxNDiRDMmm24lMAUKtdCFfftM8w/fdUyfoeFs=;
    h=references:Subject:From:Reply-To:To:Date:From;
    b=Bo0BsXAHgKiBfBtMvvO/+KaS9PuuS0+AozL4SxU05jHZcJFc7qFIPEpqkJIdbzNcQ
     wq0PJYclgX7QZDOMm3VHQwcwOxBDXAbdnpfkPM9/wa+FWKfr6ikowMTHHT3CA1qNbe
     h+BQVyBKIvr/LDFPSN2hQmfXWwWupm1lgUhJ07T4=
Content-Type: multipart/mixed; boundary="===============7355787381227985247=="
MIME-Version: 1.0
Message-Id: {extra}
references: <670034078674109.1555335454.587288856506348-openerp-32-project.task@aaa>
Subject: Re: Test
From: Mitchell Admin <admin@yourcompany.example.com>
Reply-To: YourCompany Research & Development <aaa+catchall@test.ironsky>
To: Raoul <{email_from}>
Date: Mon, 15 Apr 2019 13:40:24 -0000
X-Odoo-Objects: project.project-3, ,project.task-32
X-Spam-Status: No, score=-2.0 required=5.0 tests=ALL_TRUSTED,BAYES_00,
    DKIM_ADSP_NXDOMAIN,HEADER_FROM_DIFFERENT_DOMAINS,HTML_MESSAGE
    shortcircuit=no autolearn=no autolearn_force=no version=3.4.2
X-Spam-Checker-Version: SpamAssassin 3.4.2 (2018-09-13) on mail2.test.ironsky

--===============7355787381227985247==
Content-Type: multipart/alternative; boundary="===============8588563873240298690=="
MIME-Version: 1.0

--===============8588563873240298690==
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: base64

CgpaYm91bGl1b2l1b2l6ZWYKCi0tCkFkbWluaXN0cmF0b3IKU2VudApieQpbMV0gWW91ckNvbXBh
bnkKCnVzaW5nCk9kb28gWzJdIC4KCgoKWzFdIGh0dHA6Ly93d3cuZXhhbXBsZS5jb20KWzJdIGh0
dHBzOi8vd3d3Lm9kb28uY29tP3V0bV9zb3VyY2U9ZGImdXRtX21lZGl1bT1lbWFpbAo=

--===============8588563873240298690==
Content-Type: text/html; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: base64

CjxkaXY+CgoKPGRpdj48cD5aYm91bGl1b2l1b2l6ZWY8L3A+PC9kaXY+Cgo8ZGl2IGNsYXNzPSJm
b250LXNpemU6IDEzcHg7Ij48c3BhbiBkYXRhLW8tbWFpbC1xdW90ZT0iMSI+LS0gPGJyIGRhdGEt
by1tYWlsLXF1b3RlPSIxIj4KQWRtaW5pc3RyYXRvcjwvc3Bhbj48L2Rpdj4KPHAgc3R5bGU9ImNv
bG9yOiAjNTU1NTU1OyBtYXJnaW4tdG9wOjMycHg7Ij4KICAgIFNlbnQKICAgIDxzcGFuPgogICAg
YnkKICAgIDxhIHN0eWxlPSJ0ZXh0LWRlY29yYXRpb246bm9uZTsgY29sb3I6ICM4NzVBN0I7IiBo
cmVmPSJodHRwOi8vd3d3LmV4YW1wbGUuY29tIj4KICAgICAgICA8c3Bhbj5Zb3VyQ29tcGFueTwv
c3Bhbj4KICAgIDwvYT4KICAgIAogICAgPC9zcGFuPgogICAgdXNpbmcKICAgIDxhIHRhcmdldD0i
X2JsYW5rIiBocmVmPSJodHRwczovL3d3dy5vZG9vLmNvbT91dG1fc291cmNlPWRiJmFtcDt1dG1f
bWVkaXVtPWVtYWlsIiBzdHlsZT0idGV4dC1kZWNvcmF0aW9uOm5vbmU7IGNvbG9yOiAjODc1QTdC
OyI+T2RvbzwvYT4uCjwvcD4KPC9kaXY+CiAgICAgICAg

--===============8588563873240298690==--

--===============7355787381227985247==--

--92726A5F09.1555335666/mail2.test.ironsky--
"""

MAIL_NO_BODY = '''\
Return-Path: <{email_from}>
Delivered-To: catchall@xxxx.xxxx
Received: from in66.mail.ovh.net (unknown [10.101.4.66])
    by vr38.mail.ovh.net (Postfix) with ESMTP id 4GLCGr70Kyz1myr75
    for <catchall@xxxx.xxxx>; Thu,  8 Jul 2021 10:30:12 +0000 (UTC)
X-Comment: SPF check N/A for local connections - client-ip=213.186.33.59; helo=mail663.ha.ovh.net; envelope-from={email_from}; receiver=catchall@xxxx.xxxx 
Authentication-Results: in66.mail.ovh.net; dkim=none; dkim-atps=neutral
Delivered-To: xxxx.xxxx-{email_to}
X-ME-Helo: opme11oxm23aub.bagnolet.francetelecom.fr
X-ME-Auth: ZnJlZGVyaWMuYmxhY2hvbjA3QG9yYW5nZS5mcg==
X-ME-Date: Thu, 08 Jul 2021 12:30:11 +0200
X-ME-IP: 86.221.151.111
Date: Thu, 8 Jul 2021 12:30:11 +0200 (CEST)
From: =?UTF-8?Q?Fr=C3=A9d=C3=A9ric_BLACHON?= <{email_from}>
Reply-To: 
    =?UTF-8?Q?Fr=C3=A9d=C3=A9ric_BLACHON?= <{email_from}>
To: {email_to}
Message-ID: <1024471522.82574.1625740211606.JavaMail.open-xchange@opme11oxm23aub.bagnolet.francetelecom.fr>
Subject: transport autorisation 19T
MIME-Version: 1.0
Content-Type: multipart/mixed; 
    boundary="----=_Part_82573_178179506.1625740211587"

------=_Part_82573_178179506.1625740211587
MIME-Version: 1.0
Content-Type: text/html; charset=UTF-8
Content-Transfer-Encoding: 7bit

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">

<html xmlns="http://www.w3.org/1999/xhtml"><head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
 </head><body style="font-family: arial,helvetica,sans-serif; font-size: 13pt"></body></html>
'''

MAIL_NO_FINAL_RECIPIENT = """\
Return-Path: <bounce-md_9656353.6125275c.v1-f28f7746389e45f0bfbf9faefe9e0dc8@mandrillapp.com>
Delivered-To: catchall@xxxx.xxxx
Received: from in58.mail.ovh.net (unknown [10.101.4.58])
	by vr46.mail.ovh.net (Postfix) with ESMTP id 4GvFsq2QLYz1t0N7r
	for <catchall@xxxx.xxxx>; Tue, 24 Aug 2021 17:07:43 +0000 (UTC)
Received-SPF: Softfail (mailfrom) identity=mailfrom; client-ip=46.105.72.169; helo=40.mo36.mail-out.ovh.net; envelope-from=bounce-md_9656353.6125275c.v1-f28f7746389e45f0bfbf9faefe9e0dc8@mandrillapp.com; receiver=catchall@xxxx.xxxx 
Authentication-Results: in58.mail.ovh.net;
	dkim=pass (1024-bit key; unprotected) header.d=mandrillapp.com header.i=bounces-noreply@mandrillapp.com header.b="TDzUcdJs";
	dkim=pass (1024-bit key) header.d=mandrillapp.com header.i=@mandrillapp.com header.b="MyjddTY5";
	dkim-atps=neutral
Delivered-To: xxxx.xxxx-{email_to}
Authentication-Results: in62.mail.ovh.net;
	dkim=pass (1024-bit key; unprotected) header.d=mandrillapp.com header.i=bounces-noreply@mandrillapp.com header.b="TDzUcdJs";
	dkim=pass (1024-bit key) header.d=mandrillapp.com header.i=@mandrillapp.com header.b="MyjddTY5";
	dkim-atps=neutral
From: MAILER-DAEMON <bounces-noreply@mandrillapp.com>
Subject: Undelivered Mail Returned to Sender
To: {email_to}
X-Report-Abuse: Please forward a copy of this message, including all headers, to abuse@mandrill.com
X-Report-Abuse: You can also report abuse here: http://mandrillapp.com/contact/abuse?id=9656353.f28f7746389e45f0bfbf9faefe9e0dc8
X-Mandrill-User: md_9656353
Feedback-ID: 9656353:9656353.20210824:md
Message-Id: <9656353.20210824170740.6125275cf21879.17950539@mail9.us4.mandrillapp.com>
Date: Tue, 24 Aug 2021 17:07:40 +0000
MIME-Version: 1.0
Content-Type: multipart/report; boundary="_av-UfLe6y6qxNo54-urtAxbJQ"

--_av-UfLe6y6qxNo54-urtAxbJQ
Content-Type: text/plain; charset=utf-8
Content-Transfer-Encoding: 7bit

    --- The following addresses had delivery problems ---

<{email_from}>   (5.7.1 <{email_from}>: Recipient address rejected: Access denied)


--_av-UfLe6y6qxNo54-urtAxbJQ
Content-Type: message/delivery-status
Content-Transfer-Encoding: 7bit

Original-Recipient: <{email_from}>
Action: failed
Diagnostic-Code: smtp; 554 5.7.1 <{email_from}>: Recipient address rejected: Access denied
Remote-MTA: 10.245.192.40



--_av-UfLe6y6qxNo54-urtAxbJQ--"""

MAIL_FORWARDED = """X-Original-To: lucie@petitebedaine.fr
Delivered-To: raoul@grosbedon.fr
Delivered-To: lucie@petitebedaine.fr
To: lucie@petitebedaine.fr
From: "Bruce Wayne" <bruce@wayneenterprises.com>

SSBhbSB0aGUgQmF0TWFuCg=="""
