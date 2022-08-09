# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

MAIL_TEMPLATE = """Return-Path: {return_path}
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
