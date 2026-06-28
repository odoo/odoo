from odoo import api, fields, models


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    bancontact_id = fields.Char("Bancontact ID", readonly=True, copy=False, index='btree_not_null')

    @api.model
    def _get_additional_payment_fields(self):
        return super()._get_additional_payment_fields() + ["bancontact_id"]
