#!/usr/bin/env python
# -*- coding: utf-8 -*-

MISC_HTML_SOURCE = """
<font size="2" style="color: rgb(31, 31, 31); font-family: monospace; font-variant: normal; line-height: normal; ">test1</font>
<div style="color: rgb(31, 31, 31); font-family: monospace; font-variant: normal; line-height: normal; font-size: 12px; font-style: normal; ">
<b>test2</b></div><div style="color: rgb(31, 31, 31); font-family: monospace; font-variant: normal; line-height: normal; font-size: 12px; ">
<i>test3</i></div><div style="color: rgb(31, 31, 31); font-family: monospace; font-variant: normal; line-height: normal; font-size: 12px; ">
<u>test4</u></div><div style="color: rgb(31, 31, 31); font-family: monospace; font-variant: normal; line-height: normal; font-size: 12px; ">
<strike>test5</strike></div><div style="color: rgb(31, 31, 31); font-family: monospace; font-variant: normal; line-height: normal; ">
<font size="5">test6</font></div><div><ul><li><font color="#1f1f1f" face="monospace" size="2">test7</font></li><li>
<font color="#1f1f1f" face="monospace" size="2">test8</font></li></ul><div><ol><li><font color="#1f1f1f" face="monospace" size="2">test9</font>
</li><li><font color="#1f1f1f" face="monospace" size="2">test10</font></li></ol></div></div>
<blockquote style="margin: 0 0 0 40px; border: none; padding: 0px;"><div><div><div><font color="#1f1f1f" face="monospace" size="2">
test11</font></div></div></div></blockquote><blockquote style="margin: 0 0 0 40px; border: none; padding: 0px;">
<blockquote style="margin: 0 0 0 40px; border: none; padding: 0px;"><div><font color="#1f1f1f" face="monospace" size="2">
test12</font></div><div><font color="#1f1f1f" face="monospace" size="2"><br></font></div></blockquote></blockquote>
<font color="#1f1f1f" face="monospace" size="2"><a href="http://google.com">google</a></font>
<a href="javascript:alert('malicious code')">test link</a>
"""

EDI_LIKE_HTML_SOURCE = """<div style="font-family: 'Lucica Grande', Ubuntu, Arial, Verdana, sans-serif; font-size: 12px; color: rgb(34, 34, 34); background-color: #FFF; ">
    <p>Hello ${object.partner_id.name},</p>
    <p>A new invoice is available for you: </p>
    <p style="border-left: 1px solid #8e0000; margin-left: 30px;">
       &nbsp;&nbsp;<strong>REFERENCES</strong><br />
       &nbsp;&nbsp;Invoice number: <strong>${object.number}</strong><br />
       &nbsp;&nbsp;Invoice total: <strong>${object.amount_total} ${object.currency_id.name}</strong><br />
       &nbsp;&nbsp;Invoice date: ${object.date_invoice}<br />
       &nbsp;&nbsp;Order reference: ${object.origin}<br />
       &nbsp;&nbsp;Your contact: <a href="mailto:${object.user_id.email or ''}?subject=Invoice%20${object.number}">${object.user_id.name}</a>
    </p>
    <br/>
    <p>It is also possible to directly pay with Paypal:</p>
    <a style="margin-left: 120px;" href="${object.paypal_url}">
        <img class="oe_edi_paypal_button" src="https://www.paypal.com/en_US/i/btn/btn_paynowCC_LG.gif"/>
    </a>
    <br/>
    <p>If you have any question, do not hesitate to contact us.</p>
    <p>Thank you for choosing ${object.company_id.name or 'us'}!</p>
    <br/>
    <br/>
    <div style="width: 375px; margin: 0px; padding: 0px; background-color: #8E0000; border-top-left-radius: 5px 5px; border-top-right-radius: 5px 5px; background-repeat: repeat no-repeat;">
        <h3 style="margin: 0px; padding: 2px 14px; font-size: 12px; color: #DDD;">
            <strong style="text-transform:uppercase;">${object.company_id.name}</strong></h3>
    </div>
    <div style="width: 347px; margin: 0px; padding: 5px 14px; line-height: 16px; background-color: #F2F2F2;">
        <span style="color: #222; margin-bottom: 5px; display: block; ">
        ${object.company_id.street}<br/>
        ${object.company_id.street2}<br/>
        ${object.company_id.zip} ${object.company_id.city}<br/>
        ${object.company_id.state_id and ('%s, ' % object.company_id.state_id.name) or ''} ${object.company_id.country_id.name or ''}<br/>
        </span>
        <div style="margin-top: 0px; margin-right: 0px; margin-bottom: 0px; margin-left: 0px; padding-top: 0px; padding-right: 0px; padding-bottom: 0px; padding-left: 0px; ">
            Phone:&nbsp; ${object.company_id.phone}
        </div>
        <div>
            Web :&nbsp;<a href="${object.company_id.website}">${object.company_id.website}</a>
        </div>
    </div>
</div></body></html>"""

TEXT_1 = """I contact you about our meeting tomorrow. Here is the schedule I propose:
9 AM: brainstorming about our new amazing business app
9.45 AM: summary
10 AM: meeting with Ignasse to present our app
Is everything ok for you ?
--
MySignature"""

TEXT_1_IN = ["""I contact you about our meeting tomorrow. Here is the schedule I propose:
9 AM: brainstorming about our new amazing business app
9.45 AM: summary
10 AM: meeting with Ignasse to present our app
Is everything ok for you ?"""]
TEXT_1_OUT = ["""--
MySignature"""]

TEXT_2 = """Salut Raoul!
Le 28 oct. 2012 à 00:02, Raoul Grosbedon a écrit :

> I contact you about our meeting tomorrow. Here is the schedule I propose: (quote)

Of course. This seems viable.

> 2012/10/27 Bert Tartopoils :
>> blahblahblah (quote)?
>> 
>> blahblahblah (quote)
>> 
>> Bert TARTOPOILS
>> bert.tartopoils@miam.miam
>> 
> 
> 
> -- 
> RaoulSignature

Bert TARTOPOILS
bert.tartopoils@miam.miam
"""

TEXT_2_IN = ["Salut Raoul!", "Of course. This seems viable."]
TEXT_2_OUT = ["I contact you about our meeting tomorrow. Here is the schedule I propose: (quote)",
    """> 2012/10/27 Bert Tartopoils :
>> blahblahblah (quote)?
>> 
>> blahblahblah (quote)
>> 
>> Bert TARTOPOILS
>> bert.tartopoils@miam.miam
>> 
> 
> 
> -- 
> RaoulSignature"""]

HTML_1 = """<p>I contact you about our meeting for tomorrow. Here is the schedule I propose: (keep)
9 AM: brainstorming about our new amazing business app
9.45 AM: summary
10 AM: meeting with Ignasse to present our app
Is everything ok for you ?
--
MySignature</p>"""

HTML_1_IN = ["""I contact you about our meeting for tomorrow. Here is the schedule I propose: (keep)
9 AM: brainstorming about our new amazing business app
9.45 AM: summary
10 AM: meeting with Ignasse to present our app
Is everything ok for you ?"""]
HTML_1_OUT = ["""--
MySignature"""]

HTML_2 = """<div>
    <font><span>I contact you about our meeting for tomorrow. Here is the schedule I propose:</span></font>
</div>
<div>
    <ul>
        <li><span>9 AM: brainstorming about our new amazing business app</span></li>
        <li><span>9.45 AM: summary</span></li>
        <li><span>10 AM: meeting with Fabien to present our app</span></li>
    </ul>
</div>
<div>
    <font><span>Is everything ok for you ?</span></font>
</div>"""

HTML_2_IN = ["<font><span>I contact you about our meeting for tomorrow. Here is the schedule I propose:</span></font>",
    "<li><span>9 AM: brainstorming about our new amazing business app</span></li>",
    "<li><span>9.45 AM: summary</span></li>",
    "<li><span>10 AM: meeting with Fabien to present our app</span></li>",
    "<font><span>Is everything ok for you ?</span></font>"]
HTML_2_OUT = []

HTML_3 = """<div><pre>This is an answer.

Regards,
XXXXXX
----- Mail original -----</pre>


<pre>Hi, 


My CRM-related question.

Regards, 

XXXX</pre></div>"""

HTML_3_IN = ["""<div><pre>This is an answer.

Regards,
XXXXXX
----- Mail original -----</pre>"""]
HTML_3_OUT = ["Hi,", "My CRM-related question.",
    "Regards,"]

GMAIL_1 = """Hello,<div><br></div><div>Ok for me. I am replying directly in gmail, without signature.</div><div><br></div><div>Kind regards,</div><div><br></div><div>Demo.<br><br><div>On Thu, Nov 8, 2012 at 5:29 PM,  <span>&lt;<a href="mailto:dummy@example.com">dummy@example.com</a>&gt;</span> wrote:<br><blockquote><div>I contact you about our meeting for tomorrow. Here is the schedule I propose:</div><div><ul><li>9 AM: brainstorming about our new amazing business app&lt;/span&gt;&lt;/li&gt;</li>
<li>9.45 AM: summary</li><li>10 AM: meeting with Fabien to present our app</li></ul></div><div>Is everything ok for you ?</div>
<div><p>--<br>Administrator</p></div>

<div><p>Log in our portal at: <a href="http://localhost:8069#action=login&amp;db=mail_1&amp;login=demo">http://localhost:8069#action=login&amp;db=mail_1&amp;login=demo</a></p></div>
</blockquote></div><br></div>"""

GMAIL_1_IN = ['Ok for me. I am replying directly in gmail, without signature.']
GMAIL_1_OUT = ['Administrator', 'Log in our portal at:']

THUNDERBIRD_1 = """<div>On 11/08/2012 05:29 PM,
      <a href="mailto:dummy@example.com">dummy@example.com</a> wrote:<br></div>
    <blockquote>
      <div>I contact you about our meeting for tomorrow. Here is the
        schedule I propose:</div>
      <div>
        <ul><li>9 AM: brainstorming about our new amazing business
            app&lt;/span&gt;&lt;/li&gt;</li>
          <li>9.45 AM: summary</li>
          <li>10 AM: meeting with Fabien to present our app</li>
        </ul></div>
      <div>Is everything ok for you ?</div>
      <div>
        <p>--<br>
          Administrator</p>
      </div>
      <div>
        <p>Log in our portal at:
<a href="http://localhost:8069#action=login&amp;db=mail_1&amp;token=rHdWcUART5PhEnJRaXjH">http://localhost:8069#action=login&amp;db=mail_1&amp;token=rHdWcUART5PhEnJRaXjH</a></p>
      </div>
    </blockquote>
    Ok for me. I am replying directly below your mail, using Thunderbird, with a signature.<br><br>
    Did you receive my email about my new laptop, by the way ?<br><br>
    Raoul.<br><pre>-- 
Raoul Grosbedonn&#233;e
</pre>"""

THUNDERBIRD_1_IN = ['Ok for me. I am replying directly below your mail, using Thunderbird, with a signature.']
THUNDERBIRD_1_OUT = ['I contact you about our meeting for tomorrow.', 'Raoul Grosbedon']

HOTMAIL_1 = """<div>
    <div dir="ltr"><br>&nbsp;
        I have an amazing company, i'm learning OpenERP, it is a small company yet, but plannig to grow up quickly.
        <br>&nbsp;<br>Kindest regards,<br>xxx<br>
        <div>
            <div id="SkyDrivePlaceholder">
            </div>
            <hr id="stopSpelling">
            Subject: Re: your OpenERP.com registration<br>From: xxx@xxx.xxx<br>To: xxx@xxx.xxx<br>Date: Wed, 27 Mar 2013 17:12:12 +0000
            <br><br>
            Hello xxx,
            <br>
            I noticed you recently created an OpenERP.com account to access OpenERP Apps.
            <br>
            You indicated that you wish to use OpenERP in your own company.
            We would like to know more about your your business needs and requirements, and see how
            we can help you. When would you be available to discuss your project ?<br>
            Best regards,<br>
            <pre>
                <a href="http://openerp.com" target="_blank">http://openerp.com</a>
                Belgium: +32.81.81.37.00
                U.S.: +1 (650) 307-6736
                India: +91 (79) 40 500 100
            </pre>
        </div>
    </div>
</div>"""

HOTMAIL_1_IN = ["I have an amazing company, i'm learning OpenERP, it is a small company yet, but plannig to grow up quickly."]
HOTMAIL_1_OUT = ["Subject: Re: your OpenERP.com registration", " I noticed you recently created an OpenERP.com account to access OpenERP Apps.",
    "We would like to know more about your your business needs and requirements", "Belgium: +32.81.81.37.00"]

MSOFFICE_1 = """
<div>
<div class="WordSection1">
        <p class="MsoNormal">
            <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">
                Our requirements are simple. Just looking to replace some spreadsheets for tracking quotes and possibly using the timecard module.
                We are a company of 25 engineers providing product design services to clients.
            </span>
        </p>
        <p></p>
        <p></p>
        <p class="MsoNormal">
            <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">
                I’ll install on a windows server and run a very limited trial to see how it works.
                If we adopt OpenERP we will probably move to Linux or look for a hosted SaaS option.
            </span>
        </p>
        <p></p>
        <p></p>
        <p class="MsoNormal">
            <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">
                <br>
                I am also evaluating Adempiere and maybe others.
            </span>
        </p>
        <p></p>
        <p></p>
        <p class="MsoNormal">
            <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">
            </span>
        </p>
        <p>&nbsp;</p>
        <p></p>
        <p class="MsoNormal">
            <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">
                I expect the trial will take 2-3 months as this is not a high priority for us.
            </span>
        </p>
        <p></p>
        <p></p>
        <p class="MsoNormal">
            <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">
            </span>
        </p>
        <p>&nbsp;</p>
        <p></p>
        <p class="MsoNormal">
            <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">
                Alan
            </span>
        </p>
        <p></p>
        <p></p>
        <p class="MsoNormal">
            <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">
            </span>
        </p>
        <p>&nbsp;</p>
        <p></p>
        <div>
            <div style="border:none;border-top:solid #B5C4DF 1.0pt;padding:3.0pt 0in 0in 0in">
                <p class="MsoNormal">
                    <b><span style="font-size:10.0pt;font-family:&quot;Tahoma&quot;,&quot;sans-serif&quot;">
                        From:
                    </span></b>
                    <span style="font-size:10.0pt;font-family:&quot;Tahoma&quot;,&quot;sans-serif&quot;">
                        OpenERP Enterprise [mailto:sales@openerp.com]
                        <br><b>Sent:</b> Monday, 11 March, 2013 14:47<br><b>To:</b> Alan Widmer<br><b>Subject:</b> Re: your OpenERP.com registration
                    </span>
                </p>
                <p></p>
                <p></p>
            </div>
        </div>
        <p class="MsoNormal"></p>
        <p>&nbsp;</p>
        <p>Hello Alan Widmer, </p>
        <p></p>
        <p>I noticed you recently downloaded OpenERP. </p>
        <p></p>
        <p>
            Uou mentioned you wish to use OpenERP in your own company. Please let me more about your
            business needs and requirements? When will you be available to discuss about your project?
        </p>
        <p></p>
        <p>Thanks for your interest in OpenERP, </p>
        <p></p>
        <p>Feel free to contact me if you have any questions, </p>
        <p></p>
        <p>Looking forward to hear from you soon. </p>
        <p></p>
        <pre><p>&nbsp;</p></pre>
        <pre>--<p></p></pre>
        <pre>Nicolas<p></p></pre>
        <pre><a href="http://openerp.com">http://openerp.com</a><p></p></pre>
        <pre>Belgium: +32.81.81.37.00<p></p></pre>
        <pre>U.S.: +1 (650) 307-6736<p></p></pre>
        <pre>India: +91 (79) 40 500 100<p></p></pre>
        <pre>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<p></p></pre>
    </div>
</div>"""

MSOFFICE_1_IN = ['Our requirements are simple. Just looking to replace some spreadsheets for tracking quotes and possibly using the timecard module.']
MSOFFICE_1_OUT = ['I noticed you recently downloaded OpenERP.', 'Uou mentioned you wish to use OpenERP in your own company.']
