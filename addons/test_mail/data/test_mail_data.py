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
From: Anon <anon@odoo.com>
To: anon@gmail.com
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
