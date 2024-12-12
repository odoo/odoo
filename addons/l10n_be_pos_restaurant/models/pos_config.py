from odoo import api, models

class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _create_tax_alcohol(self):
        tax_ref = 'l10n_be_pos.tax_alcohol_luxury'
        tax = self.env.ref(tax_ref, raise_if_not_found=False)
        if not tax:
            tax = self.env['account.tax'].create({
                'name': '21% Alcohol / luxury',
                'description': '21% VAT (Alcohol, luxury)',
                'amount': 21,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
            })
            self.env['ir.model.data']._update_xmlids([{
                'xml_id': tax_ref,
                'record': tax,
                'noupdate': True,
            }])
        return tax

    def _is_belgian_fp_company(self):
        return self.env['account.fiscal.position'].search_count([('company_id', '=', self.env.company.id), ('country_id.code', '=', 'BE')]) > 0

    def _create_takeaway_fiscal_position(self, config):
        tax_21 = self.env.ref(f'account.{self.env.company.id}_attn_VAT-OUT-21-L')
        tax_12 = self.env.ref(f'account.{self.env.company.id}_attn_VAT-OUT-12-L')
        tax_6 = self.env.ref(f'account.{self.env.company.id}_attn_VAT-OUT-06-L')

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
        config.write({'takeaway': True, 'takeaway_fp_id': fp.id})

    @api.model
    def load_onboarding_bar_scenario(self):
        super().load_onboarding_bar_scenario()
        if self._is_belgian_fp_company():
            tax_alcohol = self._create_tax_alcohol()
            cocktails_category = self.env.ref('pos_restaurant.pos_category_cocktails')
            if cocktails_category:
                self.env['product.template'].search([
                    ('pos_categ_ids', 'in', [cocktails_category.id])
                ]).write({'taxes_id': [(6, 0, [tax_alcohol.id])]})

    @api.model
    def load_onboarding_restaurant_scenario(self):
        super().load_onboarding_restaurant_scenario()
        if self._is_belgian_fp_company():
            self._create_tax_alcohol()
            config = self.env.ref(self._get_suffixed_ref_name('pos_restaurant.pos_config_main_restaurant'))
            if config:
                self._create_takeaway_fiscal_position(config)
