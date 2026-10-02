from odoo import models, fields, api


class EgAccountJournal(models.Model):
    _name = "eg.account.journal"
    _rec_name = "odoo_account_journal_id"

    odoo_account_journal_id = fields.Many2one(comodel_name="account.journal", string="Payment Journal")
    name = fields.Char(related="odoo_account_journal_id.name", string="Name", store=True, readonly=True)
    instance_id = fields.Many2one(comodel_name="eg.ecom.instance", string="Instance", required=True)
    provider = fields.Selection(related="instance_id.provider", store=True)
    update_required = fields.Boolean(string="Update Required")

    # add by akash
    instance_payment_gateway_id = fields.Char(string="Instance Payment Journal ID")
