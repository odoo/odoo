from odoo import fields, models


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    bancontact_id = fields.Char("Bancontact ID", readonly=True, copy=False, index='btree_not_null')
