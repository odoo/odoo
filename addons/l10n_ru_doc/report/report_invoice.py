# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo
#    Copyright (C) 2015-2018 CodUP (<http://codup.com>).
#
##############################################################################

from odoo import api, models
from odoo.addons.l10n_ru_doc.report_helper import QWebHelper

class RuInvoiceReport(models.AbstractModel):
    _name = 'report.l10n_ru_doc.report_invoice'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move'].browse(docids)
        return {
            'helper': QWebHelper(),
            'doc_ids': docs.ids,
            'doc_model': 'account.move',
            'docs': docs
        }
