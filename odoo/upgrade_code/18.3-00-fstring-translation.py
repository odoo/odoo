import re
import itertools
import sys

log_mismatch = sys.stdout.isatty()


TRANSLATION_REGEXP = re.compile(r"""
    (?P<content>
    (?: \#\. \s module:         \s* (?P<module>     .*)     \n   )
    (?: \#\. \s odoo-python                                 \n   )?
    (?: \#\. \s odoo-javascript                             \n   )?
    (?: \#:  \s code:           \s* (?P<code>       .*)     \n   )?
    (?: \#:  \s model_terms:    \s* (?P<model_terms>.*)     \n   )*
    (?: \#:  \s model:          \s* (?P<model>      .*)     \n   )?
    (?: msgid                   \s  (?P<msgid>      (?:".*"\n)+ ))
    (?: msgstr                  \s  (?P<msgstr>     (?:".*"\n)+ ))
    )
""", re.VERBOSE)

FORMAT_REGEX = re.compile(r'(?!>)(?:#\{((?:.|\n)+?)\})|(?:\{\{((?:.|\n)+?)\}\})(?!<)')  # see odoo.tools.translate (but avoid ">{{Location name}}<")
VARNAME_REGEXP = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
TRANSLATION_BREAKLINE = re.compile(r'"\n"')
UNTRANSLATABLE_STRING = re.compile(r'''
    (?:^ | [^(\['"\\] )
    (?P<string>['"](?![0-9]+)[^'"]+['"])
    (?: [^)\]'"] | $ )
''', re.VERBOSE)


translatable_xml_fields = [
    'ir.ui.view,arch_db',
    'theme.ir.ui.view,arch',
    'knowledge.article,template_body',
    'mail.template,body_html',
    'appointment.resource,description',
    'appointment.type,message_confirmation',
    'appointment.type,message_intro',
    'helpdesk.sla,description',
    'helpdesk.team,description',
    'hr.appraisal.template,appraisal_employee_feedback_template',
    'hr.appraisal.template,appraisal_manager_feedback_template',
    'hr.appraisal,employee_feedback_template',
    'hr.appraisal,manager_feedback_template',
    'hr.contract.salary.benefit,description',
    'hr.salary.rule,note',
    'res.company,l10n_my_description',
    'room.room,description',
    'sale.order.close.reason,retention_message',
    'res.company,sign_terms',
    'res.company,sign_terms_html',
    'account.payment.term,note',
    'account.tax,description',
    'account.tax,invoice_legal_notes',
    'res.company,invoice_terms',
    'res.company,invoice_terms_html',
    'account.fiscal.position,note',
    'digest.tip,tip_description',
    'event.event,description',
    'event.event,ticket_instructions',
    'event.type,ticket_instructions',
    'event.booth.category,description',
    'event.sponsor,website_description',
    'gamification.badge,description',
    'gamification.karma.rank,description',
    'gamification.karma.rank,description_motivational',
    'forum.forum,faq',
    'forum.forum,welcome_message',
    'hr.job,description',
    'hr.job,website_description',
    'hr.resume.line,description',
    'im_livechat.channel,website_description',
    'account.move,narration',
    'lunch.alert,message',
    'lunch.product,description',
    'mail.activity.type,default_note',
    'maintenance.equipment.category,note',
    'mailing.mailing,body_arch',
    'sale.order.template,note',
    'web_tour.tour,rainbow_man_message',
    'website.menu,mega_menu_content',
    'website,robots_txt',
    'blog.blog,content',
    'blog.post,content',
    'event.track,description',
    'res.partner,website_description',
    'product.public.category,website_description',
    'product.public.category,website_footer',
    'product.template,website_description',
    'product.template,description_ecommerce',
    'product.template,out_of_stock_message',
    'slide.channel,description',
    'slide.channel,description_short',
    'slide.channel,description_html',
    'slide.slide,description',
    'res.company,report_header',
    'res.company,report_footer',
    'res.company,company_details',
    'test_new_api.prefetch,html_description',
    'test_new_api.prefetch,rare_html_description',
    'test_new_api.related_translation_1,html',
    'test.translation.import.model1,xml',
    'test.model,website_description',
]


def upgrade(file_manager):
    """ Use double quote for redacted text and single quote for strings. """
    files = [
        file for file in file_manager
        if file.path.suffix in ('.pot', '.pot')  # translation files
    ]
    if not files:
        return

    error_nb = itertools.count()
    maybe_untranslatable_terms = set()
    wrong_translation_terms = []

    def msgid_placeholder(expressions, index, g):
        expression = (g.group(1) or g.group(2)).strip()
        expression = TRANSLATION_BREAKLINE.sub('', expression)

        if UNTRANSLATABLE_STRING.findall(expression) and ('format_datetime' not in expression and '.get(' not in expression and "'#" not in expression):
            maybe_untranslatable_terms.add(expression)

        is_varname = VARNAME_REGEXP.fullmatch(expression)
        if is_varname:
            expressions[expression] = expression  # keep {{varname}}
        else:
            expressions[expression] = str(index)  # convert {{expression}} to {{index}}
        expressions[str(index)] = str(index)  # keep {{index}}
        return '{{%s}}' % (expression if is_varname else index)

    def msgstr_placeholder(expressions, g):
        expression = (g.group(1) or g.group(2)).strip()
        expression = TRANSLATION_BREAKLINE.sub('', expression)

        if expression not in expressions:
            wrong_translation_terms.append(expression)

        if expression in maybe_untranslatable_terms:
            maybe_untranslatable_terms.remove(expression)

        return '{{%s}}' % expressions.get(expression)

    def sub_translate(match, file):
        maybe_untranslatable_terms.clear()
        wrong_translation_terms.clear()

        content = match.group('content')

        if not (match.group('model_terms') or match.group('model')) or not any(f in content for f in translatable_xml_fields):
            return content

        msgid = match.group('msgid')
        index = itertools.count()
        expressions = {}
        msgid_without_py = FORMAT_REGEX.sub(lambda g: msgid_placeholder(expressions, next(index), g), msgid)

        # no terms or only numeric terms
        str_expressions = [k for k in expressions if not k.isnumeric()]
        if not str_expressions:
            return content

        msgstr = match.group('msgstr')
        msgstr_without_py = FORMAT_REGEX.sub(lambda g: msgstr_placeholder(expressions, g), msgstr)

        if wrong_translation_terms:
            next(error_nb)
            source_str = "\n             • ".join(str_expressions)
            error_str = "\n             • ".join(wrong_translation_terms)
            if log_mismatch:
                print(f'\033[93mExpression mismatch\033[39m in file: {file.path}\n    Sources: • {source_str}\n    Errors:  • {error_str}')
            return content

        if maybe_untranslatable_terms:
            source_str = "\n    • ".join(maybe_untranslatable_terms)
            if log_mismatch:
                print(f'\033[93mUntranslatable\033[39m terms detected in file: {file.path}\n    • {source_str}')

        return content.replace(msgid, msgid_without_py).replace(msgstr, msgstr_without_py)

    # Iterate over all the files and run the regexps
    for fileno, file in enumerate(files, start=1):
        # load the content
        content = file.content

        if "{{" in content or "#{" in content:
            file.content = TRANSLATION_REGEXP.sub(lambda g: sub_translate(g, file), content)

        file_manager.print_progress(fileno, len(files))

    if next(error_nb) > 1 and log_mismatch:
        print(f'\033[93m{next(error_nb) - 2} expressions mismatch in translations\033[39m')
