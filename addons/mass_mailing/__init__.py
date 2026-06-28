# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import lxml
from . import controllers
from . import models
from . import report
from . import wizard


def _update_demo_data(env):
    """
        Tweak demo data to display additional mailing features such as:
        - dynamic placeholders (can't be directly added in data because
          qweb instructions must not be interpreted during module init)
        - link trackers (need links in body_html, but body_html should be empty
          to allow its value to be computed by convert_inline)
    """
    module_mass_mailing = env['ir.module.module']._get('mass_mailing')
    if module_mass_mailing.demo:
        # mass_mail_sale_order_0
        mass_mail_sale_order_0 = env.ref('mass_mailing.mass_mail_sale_order_0')
        context = {
            'company_id': env.ref('base.main_company'),
            'res_company': env.ref('base.main_company')
        }
        mailing_header = env['ir.qweb']._render(
            'mass_mailing.s_mail_block_header_logo_and_stacked_menu',
            context
        )
        mailing_footer = env['ir.qweb']._render(
            'mass_mailing.s_mail_block_footer_social',
            context
        )
        root = lxml.html.fromstring(mass_mail_sale_order_0.body_arch)
        section = root.find('.//section')
        header = lxml.html.fromstring(mailing_header)
        footer = lxml.html.fromstring(mailing_footer)
        section.addprevious(header)
        section.addnext(footer)
        mass_mail_sale_order_0.body_arch = lxml.html.tostring(root, encoding='unicode')

        # mass_mail_1
        mass_mail_1 = env.ref('mass_mailing.mass_mail_1')
        mass_mail_1.body_html = ""
