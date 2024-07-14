# -*- coding: utf-8 -*-

from odoo import models

class IrActionsAccountReportDownload(models.AbstractModel):
    # This model is a a hack: it's sole purpose is to override _get_readable_fields
    # of ir.actions.actions to add the 'data' field which, as explained below, contains the
    # necessary parameters for report generation.
    # The reason why we don't extend the ir.actions.actions is because it's not really meant to be
    # extended outside of the base module, the risk being completely destroying the client's db.
    # If you plan on modifying this model, think of reading odoo/enterprise#13820 and/or contact
    # the metastorm team.
    _name = 'ir_actions_account_report_download'
    _description = 'Technical model for accounting report downloads'

    def _get_readable_fields(self):
        # data is not a stored field, but is used to give the parameters to generate the report
        # We keep it this way to ensure compatibility with the way former version called this action.
        return self.env['ir.actions.actions']._get_readable_fields() | {'data'}
