from odoo import api, fields, models


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    bancontact_id = fields.Char("Bancontact ID", readonly=True, copy=False, index='btree_not_null')
    bancontact_refunded_payment_id = fields.Many2one(
        'pos.payment',
        string="Refunded Bancontact Payment",
        readonly=True,
        copy=False,
        index='btree_not_null',
        help="The original Bancontact payment this refund reverses.",
    )
    bancontact_refund_ids = fields.One2many('pos.payment', 'bancontact_refunded_payment_id', string="Bancontact Refunds")
    bancontact_refund_id = fields.Char("Bancontact Refund ID", readonly=True, copy=False, index='btree_not_null')

    @api.model
    def _get_additional_payment_fields(self):
        return super()._get_additional_payment_fields() + ["bancontact_id"]

    def _bancontact_is_refundable_payment(self):
        self.ensure_one()
        return bool(
            self.bancontact_id
            and self.payment_status == 'done'
            and self.payment_method_id.bancontact_product_id.refund_enabled,
        )
