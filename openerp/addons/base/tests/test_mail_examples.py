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

OERP_WEBSITE_HTML_1 = """
<div>
    <div class="container">
        <div class="row">
            <div class="col-md-12 text-center mt16 mb16">
                <h2>OpenERP HR Features</h2>
                <h3 class="text-muted">Manage your company most important asset: People</h3>
            </div>
            <div class="col-md-4">
                <img class="img-rounded img-responsive" src="/website/static/src/img/china_thumb.jpg">
                <h4 class="mt16">Streamline Recruitments</h4>
                <p>Post job offers and keep track of each application received. Follow applicants in your recruitment process with the smart kanban view.</p>
                <p>Save time by automating some communications with email templates. Resumes are indexed automatically, allowing you to easily find for specific profiles.</p>
            </div>
            <div class="col-md-4">
                <img class="img-rounded img-responsive" src="/website/static/src/img/desert_thumb.jpg">
                <h4 class="mt16">Enterprise Social Network</h4>
                <p>Break down information silos. Share knowledge and best practices amongst all employees. Follow specific people or documents and join groups of interests to share expertise and documents.</p>
                <p>Interact with your collegues in real time with live chat.</p>
            </div>
            <div class="col-md-4">
                <img class="img-rounded img-responsive" src="/website/static/src/img/deers_thumb.jpg">
                <h4 class="mt16">Leaves Management</h4>
                <p>Keep track of the vacation days accrued by each employee. Employees enter their requests (paid holidays, sick leave, etc), for managers to approve and validate. It's all done in just a few clicks. The agenda of each employee is updated accordingly.</p>
            </div>
        </div>
    </div>
</div>"""

OERP_WEBSITE_HTML_1_IN = [
    'Manage your company most important asset: People',
    'img class="img-rounded img-responsive" src="/website/static/src/img/china_thumb.jpg"',
]
OERP_WEBSITE_HTML_1_OUT = [
    'Break down information silos.',
    'Keep track of the vacation days accrued by each employee',
    'img class="img-rounded img-responsive" src="/website/static/src/img/deers_thumb.jpg',
]

OERP_WEBSITE_HTML_2 = """
<div class="mt16 cke_widget_editable cke_widget_element oe_editable oe_dirty" data-oe-model="blog.post" data-oe-id="6" data-oe-field="content" data-oe-type="html" data-oe-translate="0" data-oe-expression="blog_post.content" data-cke-widget-data="{}" data-cke-widget-keep-attr="0" data-widget="oeref" contenteditable="true" data-cke-widget-editable="text">
    <section class="mt16 mb16">
        <div class="container">
            <div class="row">
                <div class="col-md-12 text-center mt16 mb32">
                    <h2>
                        OpenERP Project Management
                    </h2>
                    <h3 class="text-muted">Infinitely flexible. Incredibly easy to use.</h3>
                </div>
                <div class="col-md-12 mb16 mt16">
                    <p>
                        OpenERP's <b>collaborative and realtime</b> project
                        management helps your team get work done. Keep
                        track of everything, from the big picture to the
                        minute details, from the customer contract to the
                        billing.
                    </p><p>
                        Organize projects around <b>your own processes</b>. Work
                        on tasks and issues using the kanban view, schedule
                        tasks using the gantt chart and control deadlines
                        in the calendar view. Every project may have it's
                        own stages allowing teams to optimize their job.
                    </p>
                </div>
            </div>
        </div>
    </section>
    <section class="">
        <div class="container">
            <div class="row">
                <div class="col-md-6 mt16 mb16">
                    <img class="img-responsive shadow" src="/website/static/src/img/image_text.jpg">
                </div>
                <div class="col-md-6 mt32">
                    <h3>Manage Your Shops</h3>
                    <p>
                        OpenERP's Point of Sale introduces a super clean
                        interface with no installation required that runs
                        online and offline on modern hardwares.
                    </p><p>
                        It's full integration with the company inventory
                        and accounting, gives you real time statistics and
                        consolidations amongst all shops without the hassle
                        of integrating several applications.
                    </p>
                </div>
            </div>
        </div>
    </section>
    <section class="">
        <div class="container">
            <div class="row">
                <div class="col-md-6 mt32">
                    <h3>Enterprise Social Network</h3>
                    <p>
                        Make every employee feel more connected and engaged
                        with twitter-like features for your own company. Follow
                        people, share best practices, 'like' top ideas, etc.
                    </p><p>
                        Connect with experts, follow what interests you, share
                        documents and promote best practices with OpenERP
                        Social application. Get work done with effective
                        collaboration across departments, geographies
                        and business applications.
                    </p>
                </div>
                <div class="col-md-6 mt16 mb16">
                    <img class="img-responsive shadow" src="/website/static/src/img/text_image.png">
                </div>
            </div>
        </div>
    </section><section class="">
        <div class="container">
            <div class="row">
                <div class="col-md-12 text-center mt16 mb32">
                    <h2>Our Porfolio</h2>
                    <h4 class="text-muted">More than 500 successful projects</h4>
                </div>
                <div class="col-md-4">
                    <img class="img-thumbnail img-responsive" src="/website/static/src/img/deers.jpg">
                    <img class="img-thumbnail img-responsive" src="/website/static/src/img/desert.jpg">
                    <img class="img-thumbnail img-responsive" src="/website/static/src/img/china.jpg">
                </div>
                <div class="col-md-4">
                    <img class="img-thumbnail img-responsive" src="/website/static/src/img/desert.jpg">
                    <img class="img-thumbnail img-responsive" src="/website/static/src/img/china.jpg">
                    <img class="img-thumbnail img-responsive" src="/website/static/src/img/deers.jpg">
                </div>
                <div class="col-md-4">
                    <img class="img-thumbnail img-responsive" src="/website/static/src/img/landscape.jpg">
                    <img class="img-thumbnail img-responsive" src="/website/static/src/img/china.jpg">
                    <img class="img-thumbnail img-responsive" src="/website/static/src/img/desert.jpg">
                </div>
            </div>
        </div>
    </section>
</div>
"""

OERP_WEBSITE_HTML_2_IN = [
    'management helps your team get work done',
]
OERP_WEBSITE_HTML_2_OUT = [
    'Make every employee feel more connected',
    'img class="img-responsive shadow" src="/website/static/src/img/text_image.png',
]

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

HTML_4 = """
<div>
    <div>Hi Nicholas,</div>
    <br>
    <div>I'm free now. 00447710085916.</div>
    <br>
    <div>Regards,</div>
    <div>Nicholas</div>
    <br>
    <span id="OLK_SRC_BODY_SECTION">
        <div style="font-family:Calibri; font-size:11pt; text-align:left; color:black; BORDER-BOTTOM: medium none; BORDER-LEFT: medium none; PADDING-BOTTOM: 0in; PADDING-LEFT: 0in; PADDING-RIGHT: 0in; BORDER-TOP: #b5c4df 1pt solid; BORDER-RIGHT: medium none; PADDING-TOP: 3pt">
            <span style="font-weight:bold">From: </span>OpenERP Enterprise &lt;<a href="mailto:sales@openerp.com">sales@openerp.com</a>&gt;<br><span style="font-weight:bold">Reply-To: </span>&lt;<a href="mailto:sales@openerp.com">sales@openerp.com</a>&gt;<br><span style="font-weight:bold">Date: </span>Wed, 17 Apr 2013 13:30:47 +0000<br><span style="font-weight:bold">To: </span>Microsoft Office User &lt;<a href="mailto:n.saxlund@babydino.com">n.saxlund@babydino.com</a>&gt;<br><span style="font-weight:bold">Subject: </span>Re: your OpenERP.com registration<br>
        </div>
        <br>
        <div>
            <p>Hello Nicholas Saxlund, </p>
            <p>I noticed you recently registered to our OpenERP Online solution. </p>
            <p>You indicated that you wish to use OpenERP in your own company. We would like to know more about your your business needs and requirements, and see how we can help you. When would you be available to discuss your project ?
            </p>
            <p>Best regards, </p>
            <pre><a href="http://openerp.com">http://openerp.com</a>
Belgium: +32.81.81.37.00
U.S.: +1 (650) 307-6736
India: +91 (79) 40 500 100
                        </pre>
        </div>
    </span>
</div>"""

HTML_5 = """<div><pre>Hi,

I have downloaded OpenERP installer 7.0 and successfully installed the postgresql server and the OpenERP.
I created a database and started to install module by log in as administrator.
However, I was not able to install any module due to "OpenERP Server Error" as shown in the attachement.
Could you please let me know how could I fix this problem?

&nbsp;Regards,
Goh Sin Yih


________________________________
 From: OpenERP Enterprise &lt;sales@openerp.com&gt;
To: sinyih_goh@yahoo.com 
Sent: Friday, February 8, 2013 12:46 AM
Subject: Feedback From Your OpenERP Trial
 

Hello Goh Sin Yih, 
Thank you for having tested OpenERP Online. 
I noticed you started a trial of OpenERP Online (gsy) but you did not decide to keep using it. 
So, I just wanted to get in touch with you to get your feedback. Can you tell me what kind of application you were you looking for and why you didn't decide to continue with OpenERP? 
Thanks in advance for providing your feedback, 
Do not hesitate to contact me if you have any questions, 
Thanks, 
</pre>"""

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
MSOFFICE_1_OUT = ['I noticed you recently downloaded OpenERP.', 'Uou mentioned you wish to use OpenERP in your own company.', 'Belgium: +32.81.81.37.00']

MSOFFICE_2 = """
<div>
  <div class="WordSection1">
    <p class="MsoNormal">
      <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">Nicolas,</span></p><p></p>
    <p></p>
    <p class="MsoNormal" style="text-indent:.5in">
      <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">We are currently investigating the possibility of moving away from our current ERP </span></p><p></p>
    <p></p>
    <p class="MsoNormal">
      <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">
        </span></p><p>&nbsp;</p>
      
    <p></p>
    <p class="MsoNormal">
      <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">Thank You</span></p><p></p>
    <p></p>
    <p class="MsoNormal">
      <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">Matt</span></p><p></p>
    <p></p>
    <p class="MsoNormal">
      <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">
        </span></p><p>&nbsp;</p>
      
    <p></p>
    <div>
      <p class="MsoNormal">
        <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">Raoul Petitpoil</span></p><p></p>
      <p></p>
      <p class="MsoNormal">
        <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">Poil Industries</span></p><p></p>
      <p></p>
      <p class="MsoNormal">
        <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">Information Technology</span></p><p></p>
      <p></p>
      <p class="MsoNormal">
        <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">920 Super Street</span></p><p></p>
      <p></p>
      <p class="MsoNormal">
        <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">Sanchez, Pa 17046 USA</span></p><p></p>
      <p></p>
      <p class="MsoNormal">
        <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">Tel: xxx.xxx</span></p><p></p>
      <p></p>
      <p class="MsoNormal">
        <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">Fax: xxx.xxx</span></p><p></p>
      <p></p>
      <p class="MsoNormal">
        <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">Email: </span>
        <a href="mailto:raoul@petitpoil.com">
          <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:blue">raoul@petitpoil.com</span>
        </a>
        <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">
          </span></p><p></p>
        
      <p></p>
      <p class="MsoNormal">
        <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">www.poilindustries.com</span></p><p></p>
      <p></p>
      <p class="MsoNormal">
        <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">www.superproducts.com</span></p><p></p>
      <p></p>
    </div>
    <p class="MsoNormal">
      <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">
        </span></p><p>&nbsp;</p>
      
    <p></p>
    <div>
      <div style="border:none;border-top:solid #B5C4DF 1.0pt;padding:3.0pt 0in 0in 0in">
        <p class="MsoNormal">
          <b>
            <span style="font-size:10.0pt;font-family:&quot;Tahoma&quot;,&quot;sans-serif&quot;">From:</span>
          </b>
          <span style="font-size:10.0pt;font-family:&quot;Tahoma&quot;,&quot;sans-serif&quot;"> OpenERP Enterprise [mailto:sales@openerp.com] <br><b>Sent:</b> Wednesday, April 17, 2013 1:31 PM<br><b>To:</b> Matt Witters<br><b>Subject:</b> Re: your OpenERP.com registration</span></p><p></p>
        <p></p>
      </div>
    </div>
    <p class="MsoNormal"></p>
    <p>&nbsp;</p>
    <p>Hello Raoul Petitpoil, </p>
    <p></p>
    <p>I noticed you recently downloaded OpenERP. </p>
    <p></p>
    <p>You indicated that you wish to use OpenERP in your own company. We would like to know more about your your business needs and requirements, and see how we can help you. When would you be available to discuss your project ? </p>
    <p></p>
    <p>Best regards, </p>
    <p></p>
    <pre>      <p>&nbsp;</p>
    </pre>
    <pre>--<p></p></pre>
    <pre>Nicolas<p></p></pre>
    <pre>      <a href="http://openerp.com">http://openerp.com</a>
      <p></p>
    </pre>
    <pre>Belgium: +32.81.81.37.00<p></p></pre>
    <pre>U.S.: +1 (650) 307-6736<p></p></pre>
    <pre>India: +91 (79) 40 500 100<p></p></pre>
    <pre>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <p></p></pre>
  </div>
</div>"""

MSOFFICE_2_IN = ['We are currently investigating the possibility']
MSOFFICE_2_OUT = ['I noticed you recently downloaded OpenERP.', 'You indicated that you wish', 'Belgium: +32.81.81.37.00']

MSOFFICE_3 = """<div>
  <div class="WordSection1">
    <p class="MsoNormal">
      <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">Hi Nicolas&nbsp;!</span></p><p></p>
    <p></p>
    <p class="MsoNormal">
      <span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">
        </span></p><p>&nbsp;</p>
      
    <p></p>
    <p class="MsoNormal">
      <span lang="EN-US" style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">Yes I’d be glad to hear about your offers as we struggle every year with the planning/approving of LOA. </span></p><p></p>
    <p></p>
    <p class="MsoNormal">
      <span lang="EN-US" style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">I saw your boss yesterday on tv and immediately wanted to test the interface. </span></p><p></p>
    <p></p>
    <p class="MsoNormal">
      <span lang="EN-US" style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">
        </span></p><p>&nbsp;</p>

    <p></p>
    <div>
      <p class="MsoNormal">
        <b>
          <span lang="NL-BE" style="font-size:10.0pt;font-family:&quot;Trebuchet MS&quot;,&quot;sans-serif&quot;;color:gray">Bien à vous, </span></b></p><p></p><b>
        </b>
      <p></p>
      <p class="MsoNormal">
        <b>
          <span lang="NL-BE" style="font-size:10.0pt;font-family:&quot;Trebuchet MS&quot;,&quot;sans-serif&quot;;color:gray">Met vriendelijke groeten, </span></b></p><p></p><b>
        </b>
      <p></p>
      <p class="MsoNormal">
        <b>
          <span lang="EN-GB" style="font-size:10.0pt;font-family:&quot;Trebuchet MS&quot;,&quot;sans-serif&quot;;color:gray">Best regards,</span></b></p><p></p><b>
        </b>
      <p></p>
      <p class="MsoNormal">
        <b>
          <span lang="EN-GB" style="font-size:10.0pt;font-family:&quot;Trebuchet MS&quot;,&quot;sans-serif&quot;;color:gray">
            </span></b></p><p><b>&nbsp;</b></p><b>
          
        </b>
      <p></p>
      <p class="MsoNormal">
        <b>
          <span lang="EN-GB" style="font-size:10.0pt;font-family:&quot;Trebuchet MS&quot;,&quot;sans-serif&quot;;color:gray">R. Petitpoil&nbsp;&nbsp;&nbsp; <br></span>
        </b>
        <span lang="EN-GB" style="font-size:10.0pt;font-family:&quot;Trebuchet MS&quot;,&quot;sans-serif&quot;;color:gray">Human Resource Manager<b><br><br>Field Resource s.a n.v.&nbsp;&nbsp;<i> <br></i></b>Hermesstraat 6A <br>1930 Zaventem</span>
        <span lang="EN-GB" style="font-size:8.0pt;font-family:&quot;Tahoma&quot;,&quot;sans-serif&quot;;color:gray"><br></span>
        <b>
          <span lang="FR" style="font-size:10.0pt;font-family:Wingdings;color:#1F497D">(</span>
        </b>
        <b>
          <span lang="FR" style="font-size:9.0pt;font-family:Wingdings;color:#1F497D"> </span>
        </b>
        <b>
          <span lang="EN-GB" style="font-size:8.0pt;font-family:&quot;Trebuchet MS&quot;,&quot;sans-serif&quot;;color:gray">xxx.xxx &nbsp;</span>
        </b>
        <b>
          <span lang="EN-GB" style="font-size:9.0pt;font-family:&quot;Trebuchet MS&quot;,&quot;sans-serif&quot;;color:gray"><br></span>
        </b>
        <b>
          <span lang="FR" style="font-size:10.0pt;font-family:&quot;Wingdings 2&quot;;color:#1F497D">7</span>
        </b>
        <b>
          <span lang="FR" style="font-size:9.0pt;font-family:&quot;Wingdings 2&quot;;color:#1F497D"> </span>
        </b>
        <b>
          <span lang="EN-GB" style="font-size:8.0pt;font-family:&quot;Trebuchet MS&quot;,&quot;sans-serif&quot;;color:gray">+32 2 727.05.91<br></span>
        </b>
        <span lang="EN-GB" style="font-size:24.0pt;font-family:Webdings;color:green">P</span>
        <span lang="EN-GB" style="font-size:8.0pt;font-family:&quot;Tahoma&quot;,&quot;sans-serif&quot;;color:green"> <b>&nbsp;&nbsp; </b></span>
        <b>
          <span lang="EN-GB" style="font-size:9.0pt;font-family:&quot;Trebuchet MS&quot;,&quot;sans-serif&quot;;color:green">Please consider the environment before printing this email.</span>
        </b>
        <span lang="EN-GB" style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:navy"> </span>
        <span lang="EN-GB" style="font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:navy">
          </span></p><p></p>
        
      <p></p>
    </div>
    <p class="MsoNormal">
      <span lang="EN-US" style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">
        </span></p><p>&nbsp;</p>
      
    <p></p>
    <div>
      <div style="border:none;border-top:solid #B5C4DF 1.0pt;padding:3.0pt 0cm 0cm 0cm">
        <p class="MsoNormal">
          <b>
            <span lang="FR" style="font-size:10.0pt;font-family:&quot;Tahoma&quot;,&quot;sans-serif&quot;">De&nbsp;:</span>
          </b>
          <span lang="FR" style="font-size:10.0pt;font-family:&quot;Tahoma&quot;,&quot;sans-serif&quot;"> OpenERP Enterprise [mailto:sales@openerp.com] <br><b>Envoyé&nbsp;:</b> jeudi 18 avril 2013 11:31<br><b>À&nbsp;:</b> Paul Richard<br><b>Objet&nbsp;:</b> Re: your OpenERP.com registration</span></p><p></p>
        <p></p>
      </div>
    </div>
    <p class="MsoNormal"></p>
    <p>&nbsp;</p>
    <p>Hello Raoul PETITPOIL, </p>
    <p></p>
    <p>I noticed you recently registered to our OpenERP Online solution. </p>
    <p></p>
    <p>You indicated that you wish to use OpenERP in your own company. We would like to know more about your your business needs and requirements, and see how we can help you. When would you be available to discuss your project ? </p>
    <p></p>
    <p>Best regards, </p>
    <p></p>
    <pre>      <p>&nbsp;</p>
    </pre>
    <pre>--<p></p></pre>
    <pre>Nicolas<p></p></pre>
    <pre>      <a href="http://openerp.com">http://openerp.com</a>
      <p></p>
    </pre>
    <pre>Belgium: +32.81.81.37.00<p></p></pre>
    <pre>U.S.: +1 (650) 307-6736<p></p></pre>
    <pre>India: +91 (79) 40 500 100<p></p></pre>
    <pre>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <p></p></pre>
  </div>
</div>"""

MSOFFICE_3_IN = ['I saw your boss yesterday']
MSOFFICE_3_OUT = ['I noticed you recently downloaded OpenERP.', 'You indicated that you wish', 'Belgium: +32.81.81.37.00']


# ------------------------------------------------------------
# Test cases coming from bugs
# ------------------------------------------------------------

# bug: read more not apparent, strange message in read more span
BUG1 = """<pre>Hi Migration Team,

Paragraph 1, blah blah blah blah blah blah blah blah blah blah blah blah 
blah blah blah blah blah blah blah blah blah blah blah blah blah blah 
blah blah blah blah blah blah blah blah blah blah blah blah blah blah 
blah blah blah blah blah blah blah blah blah blah blah blah blah blah 
blah blah blah blah blah blah blah blah blah blah blah blah blah blah 
blah blah blah blah blah blah blah blah blah blah blah blah blah blah 
blah blah blah blah blah blah blah blah.

Paragraph 2, blah blah blah blah blah blah blah blah blah blah blah blah 
blah blah blah blah blah blah blah blah blah blah blah blah blah blah 
blah blah blah blah blah blah blah blah blah blah blah blah blah blah 
blah blah blah blah blah blah blah blah blah blah blah blah blah blah 
blah blah blah blah blah blah blah blah blah blah blah blah blah blah 
blah blah blah blah blah blah blah blah blah blah blah blah blah blah 
blah blah blah blah blah blah blah blah.

Paragraph 3, blah blah blah blah blah blah blah blah blah blah blah blah 
blah blah blah blah blah blah blah blah blah blah blah blah blah blah 
blah blah blah blah blah blah blah blah blah blah blah blah blah blah 
blah blah blah blah blah blah blah blah blah blah blah blah blah blah 
blah blah blah blah blah blah blah blah blah blah blah blah blah blah 
blah blah blah blah blah blah blah blah blah blah blah blah blah blah 
blah blah blah blah blah blah blah blah.

Thanks.

Regards,

-- 
Olivier Laurent
Migration Manager
OpenERP SA
Chaussée de Namur, 40
B-1367 Gérompont
Tel: +32.81.81.37.00
Web: http://www.openerp.com</pre>"""

BUG_1_IN = [
    'Hi Migration Team',
    'Paragraph 1'
]
BUG_1_OUT = [
    'Olivier Laurent',
    'Chaussée de Namur',
    '81.81.37.00',
    'openerp.com',
]


BUG2 = """
<div>
    <br>
    <div class="moz-forward-container"><br>
      <br>
      -------- Original Message --------
      <table class="moz-email-headers-table" border="0" cellpadding="0" cellspacing="0">
        <tbody>
          <tr>
            <th nowrap="" valign="BASELINE" align="RIGHT">Subject:
            </th>
            <td>Fwd: TR: OpenERP S.A. Payment Reminder</td>
          </tr>
          <tr>
            <th nowrap="" valign="BASELINE" align="RIGHT">Date: </th>
            <td>Wed, 16 Oct 2013 14:11:13 +0200</td>
          </tr>
          <tr>
            <th nowrap="" valign="BASELINE" align="RIGHT">From: </th>
            <td>Christine Herrmann <a class="moz-txt-link-rfc2396E" href="mailto:che@openerp.com">&lt;che@openerp.com&gt;</a></td>
          </tr>
          <tr>
            <th nowrap="" valign="BASELINE" align="RIGHT">To: </th>
            <td><a class="moz-txt-link-abbreviated" href="mailto:online@openerp.com">online@openerp.com</a></td>
          </tr>
        </tbody>
      </table>
      <br>
      <br>
      
      <br>
      <div class="moz-forward-container"><br>
        <br>
        -------- Message original --------
        <table class="moz-email-headers-table" border="0" cellpadding="0" cellspacing="0">
          <tbody>
            <tr>
              <th nowrap="" valign="BASELINE" align="RIGHT">Sujet:
              </th>
              <td>TR: OpenERP S.A. Payment Reminder</td>
            </tr>
            <tr>
              <th nowrap="" valign="BASELINE" align="RIGHT">Date&nbsp;:
              </th>
              <td>Wed, 16 Oct 2013 10:34:45 -0000</td>
            </tr>
            <tr>
              <th nowrap="" valign="BASELINE" align="RIGHT">De&nbsp;: </th>
              <td>Ida Siwatala <a class="moz-txt-link-rfc2396E" href="mailto:infos@inzoservices.com">&lt;infos@inzoservices.com&gt;</a></td>
            </tr>
            <tr>
              <th nowrap="" valign="BASELINE" align="RIGHT">Répondre

                à&nbsp;: </th>
              <td><a class="moz-txt-link-abbreviated" href="mailto:catchall@mail.odoo.com">catchall@mail.odoo.com</a></td>
            </tr>
            <tr>
              <th nowrap="" valign="BASELINE" align="RIGHT">Pour&nbsp;:
              </th>
              <td>Christine Herrmann (che) <a class="moz-txt-link-rfc2396E" href="mailto:che@openerp.com">&lt;che@openerp.com&gt;</a></td>
            </tr>
          </tbody>
        </table>
        <br>
        <br>
        <div>
          <div class="WordSection1">
            <p class="MsoNormal"><span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">Bonjour,</span></p>
            <p class="MsoNormal"><span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D"></span></p>
            <p>&nbsp;</p>
            <p class="MsoNormal"><span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">Pourriez-vous

                me faire un retour sur ce point.</span></p>
            <p class="MsoNormal"><span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D"></span></p>
            <p>&nbsp;</p>
            <p class="MsoNormal"><span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">Cordialement</span></p>
            <p class="MsoNormal"><span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D"></span></p>
            <p>&nbsp;</p>
            <div>
              <div style="border:none;border-top:solid #B5C4DF
                1.0pt;padding:3.0pt 0cm 0cm 0cm">
                <p class="MsoNormal"><b><span style="font-size:10.0pt;font-family:&quot;Tahoma&quot;,&quot;sans-serif&quot;">De&nbsp;:</span></b><span style="font-size:10.0pt;font-family:&quot;Tahoma&quot;,&quot;sans-serif&quot;">
                    Ida Siwatala [<a class="moz-txt-link-freetext" href="mailto:infos@inzoservices.com">mailto:infos@inzoservices.com</a>]
                    <br>
                    <b>Envoyé&nbsp;:</b> vendredi 4 octobre 2013 20:03<br>
                    <b>À&nbsp;:</b> 'Followers of
                    INZO-services-8-all-e-Maxime-Lisbonne-77176-Savigny-le-temple-France'<br>
                    <b>Objet&nbsp;:</b> RE: OpenERP S.A. Payment Reminder</span></p>
              </div>
            </div>
            <p>&nbsp;</p>
            <p class="MsoNormal"><span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">Bonsoir,</span></p>
            <p class="MsoNormal"><span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D"></span></p>
            <p>&nbsp;</p>
            <p class="MsoNormal"><span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">Je

                me permets de revenir vers vous par écrit , car j’ai
                fait 2 appels vers votre service en exposant mon
                problème, mais je n’ai pas eu de retour.</span></p>
            <p class="MsoNormal"><span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">Cela

                fait un mois que j’ai fait la souscription de votre
                produit, mais je me rends compte qu’il est pas adapté à
                ma situation ( fonctionnalité manquante et surtout je
                n’ai pas beaucoup de temps à passer à résoudre des
                bugs). </span></p>
            <p class="MsoNormal"><span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">C’est

                pourquoi , j’ai demandé qu’un accord soit trouvé avec
                vous pour annuler le contrat (tout en vous payant le
                mois d’utilisation de septembre).</span></p>
            <p class="MsoNormal"><span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D"></span></p>
            <p>&nbsp;</p>
            <p class="MsoNormal"><span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">Pourriez-vous

                me faire un retour sur ce point.</span></p>
            <p class="MsoNormal"><span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D"></span></p>
            <p>&nbsp;</p>
            <p class="MsoNormal"><span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">Cordialement,</span></p>
            <p class="MsoNormal"><span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D"></span></p>
            <p>&nbsp;</p>
            <p class="MsoNormal"><span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D">Ida

                Siwatala</span></p>
            <p class="MsoNormal"><span style="font-size:11.0pt;font-family:&quot;Calibri&quot;,&quot;sans-serif&quot;;color:#1F497D"></span></p>
            <p>&nbsp;</p>
            <p class="MsoNormal"><b><span style="font-size:10.0pt;font-family:&quot;Tahoma&quot;,&quot;sans-serif&quot;">De&nbsp;:</span></b><span style="font-size:10.0pt;font-family:&quot;Tahoma&quot;,&quot;sans-serif&quot;">
                <a href="mailto:che@openerp.com">che@openerp.com</a>
                [<a href="mailto:che@openerp.com">mailto:che@openerp.com</a>]
                <br>
                <b>Envoyé&nbsp;:</b> vendredi 4 octobre 2013 17:41<br>
                <b>À&nbsp;:</b> <a href="mailto:infos@inzoservices.com">infos@inzoservices.com</a><br>
                <b>Objet&nbsp;:</b> OpenERP S.A. Payment Reminder</span></p>
            <p>&nbsp;</p>
            <div>
              <p style="background:white"><span style="font-size:9.0pt;font-family:&quot;Arial&quot;,&quot;sans-serif&quot;;color:#222222">Dear

                  INZO services,</span></p>
              <p style="background:white"><span style="font-size:9.0pt;font-family:&quot;Arial&quot;,&quot;sans-serif&quot;;color:#222222">Exception

                  made if there was a mistake of ours, it seems that the
                  following amount stays unpaid. Please, take
                  appropriate measures in order to carry out this
                  payment in the next 8 days. </span></p>
              <p class="MsoNormal" style="background:white"><span style="font-size:9.0pt;font-family:&quot;Arial&quot;,&quot;sans-serif&quot;;color:#222222"></span></p>
              <p>&nbsp;</p>
              <table class="MsoNormalTable" style="width:100.0%;border:outset 1.5pt" width="100%" border="1" cellpadding="0">
                <tbody>
                  <tr>
                    <td style="padding:.75pt .75pt .75pt .75pt">
                      <p class="MsoNormal">Date de facturation</p>
                    </td>
                    <td style="padding:.75pt .75pt .75pt .75pt">
                      <p class="MsoNormal">Description</p>
                    </td>
                    <td style="padding:.75pt .75pt .75pt .75pt">
                      <p class="MsoNormal">Reference</p>
                    </td>
                    <td style="padding:.75pt .75pt .75pt .75pt">
                      <p class="MsoNormal">Due Date</p>
                    </td>
                    <td style="padding:.75pt .75pt .75pt .75pt">
                      <p class="MsoNormal">Amount (€)</p>
                    </td>
                    <td style="padding:.75pt .75pt .75pt .75pt">
                      <p class="MsoNormal">Lit.</p>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding:.75pt .75pt .75pt .75pt">
                      <p class="MsoNormal"><b>2013-09-24</b></p>
                    </td>
                    <td style="padding:.75pt .75pt .75pt .75pt">
                      <p class="MsoNormal"><b>2013/1121</b></p>
                    </td>
                    <td style="padding:.75pt .75pt .75pt .75pt">
                      <p class="MsoNormal"><b>Enterprise - Inzo Services
                          - Juillet 2013</b></p>
                    </td>
                    <td style="padding:.75pt .75pt .75pt .75pt">
                      <p class="MsoNormal"><b>2013-09-24</b></p>
                    </td>
                    <td style="padding:.75pt .75pt .75pt .75pt">
                      <p class="MsoNormal"><b>420.0</b></p>
                    </td>
                    <td style="padding:.75pt .75pt .75pt .75pt"><br>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding:.75pt .75pt .75pt .75pt"><br>
                    </td>
                    <td style="border:none;padding:.75pt .75pt .75pt
                      .75pt"><br>
                    </td>
                    <td style="border:none;padding:.75pt .75pt .75pt
                      .75pt"><br>
                    </td>
                    <td style="border:none;padding:.75pt .75pt .75pt
                      .75pt"><br>
                    </td>
                    <td style="border:none;padding:.75pt .75pt .75pt
                      .75pt"><br>
                    </td>
                    <td style="border:none;padding:.75pt .75pt .75pt
                      .75pt"><br>
                    </td>
                  </tr>
                </tbody>
              </table>
              <p class="MsoNormal" style="text-align:center;background:white" align="center"><span style="font-size:9.0pt;font-family:&quot;Arial&quot;,&quot;sans-serif&quot;;color:#222222">Amount

                  due : 420.00 € </span></p>
              <p style="background:white"><span style="font-size:9.0pt;font-family:&quot;Arial&quot;,&quot;sans-serif&quot;;color:#222222">Would

                  your payment have been carried out after this mail was
                  sent, please ignore this message. Do not hesitate to
                  contact our accounting department. </span></p>
              <p class="MsoNormal" style="background:white"><span style="font-size:9.0pt;font-family:&quot;Arial&quot;,&quot;sans-serif&quot;;color:#222222"><br>
                  Best Regards, <br>
                  Aurore Lesage <br>
                  OpenERP<br>
                  Chaussée de Namur, 40 <br>
                  B-1367 Grand Rosières <br>
                  Tel: +32.81.81.37.00 - Fax: +32.81.73.35.01 <br>
                  E-mail : <a href="mailto:ale@openerp.com">ale@openerp.com</a> <br>
                  Web: <a href="http://www.openerp.com">http://www.openerp.com</a></span></p>
            </div>
          </div>
        </div>
        --<br>
        INZO services <small>Sent by <a style="color:inherit" href="http://www.openerp.com">OpenERP
            S.A.</a> using <a style="color:inherit" href="https://www.openerp.com/">OpenERP</a>.</small>
        <small>Access your messages and documents <a style="color:inherit" href="https://accounts.openerp.com?db=openerp#action=mail.action_mail_redirect&amp;login=che&amp;message_id=5750830">in

            OpenERP</a></small> <br>
        <pre class="moz-signature" cols="72">-- 
Christine Herrmann 

OpenERP 
Chaussée de Namur, 40 
B-1367 Grand Rosières 
Tel: +32.81.81.37.00 - Fax: +32.81.73.35.01 

Web: <a class="moz-txt-link-freetext" href="http://www.openerp.com">http://www.openerp.com</a> </pre>
        <br>
      </div>
      <br>
      <br>
    </div>
    <br>
  
</div>"""

BUG_2_IN = [
    'read more',
    '...',
]
BUG_2_OUT = [
    'Fwd: TR: OpenERP S.A'
    'fait un mois'
]


# BUG 20/08/2014: READ MORE NOT APPEARING
BUG3 = """<div class="oe_msg_body_long" style="/* display: none; */"><p>OpenERP has been upgraded to version 8.0.</p>
<h2>What's new in this upgrade?</h2>
<div class="document">
<ul>
<li><p class="first">New Warehouse Management System:</p>
<blockquote>
<p>Schedule your picking, packing, receptions and internal moves automatically with Odoo using
your own routing rules. Define push and pull rules to organize a warehouse or to manage
product moves between several warehouses. Track in detail all stock moves, not only in your
warehouse but wherever else it's taken as well (customers, suppliers or manufacturing
locations).</p>
</blockquote>
</li>
<li><p class="first">New Product Configurator</p>
</li>
<li><p class="first">Documentation generation from website forum:</p>
<blockquote>
<p>New module to generate a documentation from questions and responses from your forum.
The documentation manager can define a table of content and any user, depending their karma,
can link a question to an entry of this TOC.</p>
</blockquote>
</li>
<li><p class="first">New kanban view of documents (resumes and letters in recruitement, project documents...)</p>
</li>
<li><p class="first">E-Commerce:</p>
<blockquote>
<ul class="simple">
<li>Manage TIN in contact form for B2B.</li>
<li>Dedicated salesteam to easily manage leads and orders.</li>
</ul>
</blockquote>
</li>
<li><p class="first">Better Instant Messaging.</p>
</li>
<li><p class="first">Faster and Improved Search view: Search drawer now appears on top of the results, and is open
by default in reporting views</p>
</li>
<li><p class="first">Improved User Interface:</p>
<blockquote>
<ul class="simple">
<li>Popups has changed to be more responsive on tablets and smartphones.</li>
<li>New Stat Buttons: Forms views have now dynamic buttons showing some statistics abouts linked models.</li>
<li>Color code to check in one look availability of components in an MRP order.</li>
<li>Unified menu bar allows you to switch easily between the frontend (website) and backend</li>
<li>Results panel is now scrollable independently of the menu bars, keeping the navigation,
search bar and view switcher always within reach.</li>
</ul>
</blockquote>
</li>
<li><p class="first">User signature is now in HTML.</p>
</li>
<li><p class="first">New development API.</p>
</li>
<li><p class="first">Remove support for Outlook and Thunderbird plugins</p>
</li>
</ul>
</div>
<p>Enjoy the new OpenERP Online!</p><span class="oe_mail_reduce"><a href="#">read less</a></span></div>"""

BUG_3_IN = [
    'read more',
    '...',
]
BUG_3_OUT = [
    'New kanban view of documents'
]
