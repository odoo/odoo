# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def get_paperformat(self):
        # force the right format (euro/A4) when sending letters, only if we are not using the l10n_DE layout
        res = super(IrActionsReport, self).get_paperformat()
        if self.env.context.get('snailmail_layout') and res != self.env.ref('l10n_de.paperformat_euro_din', False):
            paperformat_id = self.env.ref('base.paperformat_euro')
            return paperformat_id
        else:
            return res
