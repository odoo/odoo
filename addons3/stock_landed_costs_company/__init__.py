# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

def _stock_landed_costs_company_post_init(env):
    env.cr.execute("""
        UPDATE stock_landed_cost cost
        SET company_id = journal.company_id
        FROM account_journal journal
        WHERE cost.account_journal_id = journal.id
    """)
