from lxml import html


def _parse_ict_job_application(msg):
    tree = html.fromstring(msg.get('body'))
    text_elements = tree.xpath("//text()")
    success_parse = False
    mail_index = 0

    for text in text_elements:
        if "@" in text:
            break
        mail_index += 1
    try:
        email = text_elements[mail_index]
        name = text_elements[mail_index - 2]
        first_name = text_elements[mail_index - 4]
        success_parse = True
    except IndexError:
        email = ''
        name = ''
        first_name = ''

    return {
        'name': msg.get('subject'),
        'partner_name': f'{first_name} {name}',
        'applicant_email_from': email,
        'website_fields': {},
        'success_parse': success_parse,
    }


def _parse_linkedin_application(msg):
    success_parse = False
    tree = html.fromstring(msg.get('body'))
    text_elements = tree.xpath("//text()")
    href_elements = tree.xpath("//a/@href")
    name_index = 0

    for text in text_elements:
        if "·" in text:
            break
        name_index += 1
    try:
        applicant_name = text_elements[name_index-1]
        linkedin_application = href_elements[1]
        success_parse = True
    except IndexError:
        applicant_name = ''
        linkedin_application = ''

    return {
        'name': msg.get('subject'),
        'partner_name': applicant_name.strip(),
        'applicant_email_from': "",
        'success_parse': success_parse,
        'website_fields': {'linkedin_profile': linkedin_application}
    }


JOB_POSTING_SERVICE_MAILS = {
    "jobs-listings@linkedin.com": "LinkedIn",
    "applications@email.ictjob.be": "ICTJobs"
}

JOB_OFFER_PARSERS = {
    'LinkedIn': _parse_linkedin_application,
    'ICTJobs': _parse_ict_job_application,
}
