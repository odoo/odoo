from odoo import models


class Ir_Actions_Account_Report_Download(models.AbstractModel):
    # This model is a hack: its sole purpose is to override _get_fields_readable of
    # ir.actions.actions to add the 'data' field, which holds the parameters needed
    # for report generation.
    # ir.actions.actions is not extended directly because it isn't meant to be extended
    # outside of the base module, the risk being completely destroying the client's db.
    _name = "ir_actions_account_report_download"

    _description = "Technical model for report downloads"

    def _get_fields_readable(self):
        # data is not a stored field, but is used to give the parameters to generate the report
        # We keep it this way to ensure compatibility with the way former version called this action.
        return self.env["ir.actions.actions"]._get_fields_readable() | {"data"}
