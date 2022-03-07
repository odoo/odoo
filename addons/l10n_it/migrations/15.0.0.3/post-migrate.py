# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID

def migrate(cr, version):

    cr.execute("""
        INSERT INTO account_account_account_tag
        SELECT account.id, template_tag.account_account_tag_id
        FROM account_account_template AS template
        JOIN account_account AS account
            ON account.code LIKE CONCAT(template.code, '%')
        JOIN account_account_template_account_tag AS template_tag
            ON template.id = template_tag.account_account_template_id
        JOIN res_company ON res_company.id = account.company_id
        JOIN res_country ON res_country.id = res_company.account_fiscal_country_id
            AND res_country.code = 'IT'
    """)
