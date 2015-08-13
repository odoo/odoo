# -*- coding: utf-8 -*-

from openerp import models, fields, api, _

class AccountJournal(models.Model):
    _inherit = "account.journal"

    bank_statements_source = fields.Selection(selection_add=[("file_import", "File Import")])
