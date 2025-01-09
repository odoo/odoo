from odoo import api, models

class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _create_takeaway_fiscal_position(self, config):
        ChartTemplate = self.env['account.chart.template'].with_company(self.env.company)
        tax_21 = ChartTemplate.ref('attn_VAT-OUT-21-L', raise_if_not_found=False)
        tax_12 = ChartTemplate.ref('attn_VAT-OUT-12-L', raise_if_not_found=False)
        tax_6 = ChartTemplate.ref('attn_VAT-OUT-06-L', raise_if_not_found=False)

        if tax_21 and tax_12 and tax_6:
            fp = self.env['account.fiscal.position'].create({
                'name': 'Take out',
            })
            self.env['account.fiscal.position.tax'].create({
                'tax_src_id': tax_21.id,
                'tax_dest_id': tax_6.id,
                'position_id': fp.id
            })
            self.env['account.fiscal.position.tax'].create({
                'tax_src_id': tax_12.id,
                'tax_dest_id': tax_6.id,
                'position_id': fp.id
            })
            takeaway_preset = self.env.ref('pos_restaurant.pos_takeout_preset', raise_if_not_found=False)
            if takeaway_preset:
                takeaway_preset.write({'fiscal_position_id': fp.id})

    @api.model
    def load_onboarding_bar_scenario(self):
        super().load_onboarding_bar_scenario()
        if (self.env.company.chart_template or '').startswith('be'):
            ChartTemplate = self.env['account.chart.template'].with_company(self.env.company)
            tax_alcohol = ChartTemplate.ref('tax_alcohol_luxury')
            cocktails_category = self.env.ref('pos_restaurant.pos_category_cocktails', raise_if_not_found=False)
            if cocktails_category:
                self.env['product.template'].search([
                    ('pos_categ_ids', 'in', [cocktails_category.id])
                ]).write({'taxes_id': [(6, 0, [tax_alcohol.id])]})

    @api.model
    def load_onboarding_restaurant_scenario(self):
        super().load_onboarding_restaurant_scenario()
        if (self.env.company.chart_template or '').startswith('be'):
            config = self.env.ref(self._get_suffixed_ref_name('pos_restaurant.pos_config_main_restaurant'), raise_if_not_found=False)
            if config:
                self._create_takeaway_fiscal_position(config)
