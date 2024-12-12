from odoo import models

class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _configure_fiscal_position_and_pricelist(self):
        """
        Set fiscal position for urban piper.
        """
        self.ensure_one()
        if self.env['ir.module.module'].search([('name', '=', 'pos_urban_piper')]).state == 'installed' and self.env.company.account_fiscal_country_id.code == 'IN':
            fiscal_position = self.env.ref(f'account.{self.env.company.id}_fiscal_postion_in_sales_via_food_aggregator', raise_if_not_found=False)
            if fiscal_position:
                self.urbanpiper_fiscal_position_id = fiscal_position
        super()._configure_fiscal_position_and_pricelist()

