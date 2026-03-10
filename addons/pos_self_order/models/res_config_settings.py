from odoo import api, fields, models
from odoo.fields import Domain


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_self_ordering_mode = fields.Selection(related="pos_config_id.self_ordering_mode", readonly=False, required=True)

    def pos_close_ui(self):
        if self.pos_self_ordering_mode == "kiosk":
            if self.env.context.get('pos_config_id'):
                pos_config_id = self.env.context['pos_config_id']
                pos_config = self.env['pos.config'].browse(pos_config_id)
                return pos_config.action_close_kiosk_session()
        return super().pos_close_ui()

    @api.depends('pos_self_ordering_mode')
    def _compute_pos_pricelist_id(self):
        super()._compute_pos_pricelist_id()
        for res_config in self:
            if res_config.pos_self_ordering_mode == 'kiosk':
                currency_id = res_config.pos_journal_id.currency_id.id if res_config.pos_journal_id.currency_id else res_config.pos_config_id.company_id.currency_id.id
                domain = Domain.AND([self.env['product.pricelist']._check_company_domain(res_config.pos_config_id.company_id), [('currency_id', '=', currency_id)]])
                res_config.pos_available_pricelist_ids = self.env['product.pricelist'].search(domain)
