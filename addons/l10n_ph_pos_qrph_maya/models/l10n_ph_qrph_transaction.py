# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class L10n_PhQrphTransaction(models.Model):
    _inherit = 'l10n_ph.qrph.transaction'

    # An order is only stored once it is paid, but codes are minted while it is still being keyed
    # in: the uuid is what ties them to it until it exists.
    pos_order_uuid = fields.Char(string="Order UUID", readonly=True, index='btree_not_null')

    def _get_supported_models(self):
        return super()._get_supported_models() + ['pos.order']

    @api.model
    def _get_record_vals(self, res_model, res_id):
        if res_model == 'pos.order':
            # sudo: the cashier or the kiosk minting the code may not read the orders.
            order = self.env['pos.order'].sudo().search([('uuid', '=', res_id)], limit=1)
            return {'res_model': res_model, 'res_id': order.id, 'pos_order_uuid': res_id}
        return super()._get_record_vals(res_model, res_id)

    @api.model
    def _get_latest_transaction(self, model, model_id):
        if model == 'pos.order':
            if not model_id:
                return self.browse()
            return self.search([('pos_order_uuid', '=', model_id)], limit=1)
        return super()._get_latest_transaction(model, model_id)
