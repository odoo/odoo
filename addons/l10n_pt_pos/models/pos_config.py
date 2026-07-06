from odoo import _, fields, models
from odoo.exceptions import RedirectWarning


class PosConfig(models.Model):
    _inherit = 'pos.config'

    country_code = fields.Char(related='company_id.account_fiscal_country_id.code')

    def get_limited_partners_loading(self, offset=0):
        partner_ids = super().get_limited_partners_loading(offset)
        final_consumer = self.env.ref('l10n_pt_certification.pt_final_consumer', raise_if_not_found=False)
        if final_consumer and (final_consumer.id,) not in partner_ids:
            partner_ids.append((final_consumer.id,))
        return partner_ids

    def _load_pos_data_read(self, records, config):
        data = super()._load_pos_data_read(records, config)
        if data and config.country_code == 'PT':
            final_consumer = self.env.ref('l10n_pt_certification.pt_final_consumer', raise_if_not_found=False)
            data[0]['_l10n_pt_final_consumer_id'] = final_consumer.id if final_consumer else None
        return data

    def _l10n_pt_pos_verify_config(self):
        if incorrect_products := self.env['product.product'].search([
            '|', ('default_code', '=', False), ('taxes_id', '=', False),
            ('available_in_pos', '=', True),
            ('combo_ids', '=', False),
            ('categ_id', 'in', self.iface_available_categ_ids.ids),
        ]):
            raise RedirectWarning(
                _("All products should have one tax and an internal reference."),
                {
                    'type': 'ir.actions.act_window',
                    'name': 'Incorrect products',
                    'res_model': 'product.product',
                    'view_mode': 'list',
                    'views': [(self.env.ref('l10n_pt_pos.incorrect_products_view_list_pt').id, 'list'), (False, 'form')],
                    'domain': [('id', 'in', incorrect_products.ids)],
                },
                _("Incorrect products")
            )

        payment_methods = self.env['pos.payment.method'].search([('config_ids', 'in', self.ids)])
        missing_payment_mechanism = payment_methods.filtered(lambda pm: not pm.l10n_pt_pos_payment_mechanism)
        msg = ""
        if missing_payment_mechanism:
            msg += _("All payment methods available for this Point of Sale should have a payment mechanism. ")
        if msg:
            raise RedirectWarning(
                msg,
                {
                    'type': 'ir.actions.act_window',
                    'name': 'Payment Methods',
                    'res_model': 'pos.payment.method',
                    'view_mode': 'list',
                    'views': [[False, 'list'], [False, 'form']],
                    'domain': [('id', 'in', missing_payment_mechanism.ids)],
                },
                _("See Payment Methods"),
            )

    def open_ui(self):
        for config in self:
            if not config.company_id.country_id or config.country_code != 'PT':
                continue
            config._l10n_pt_pos_verify_config()
        return super().open_ui()
