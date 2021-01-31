# ©  2015-2019 Deltatech
# See README.rst file on addons root folder for license details


from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    no_negative_stock = fields.Boolean(
        string="No negative stock", default=True, help="Allows you to prohibit negative stock quantities."
    )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    no_negative_stock = fields.Boolean(
        related="company_id.no_negative_stock",
        string="No negative stock",
        readonly=False,
        help="Allows you to prohibit negative stock quantities.",
    )

    #
    # @api.model
    # def get_values(self):
    #     res = super(ResConfigSettings, self).get_values()
    #     res.update(
    #         no_negative_stock=self.env['ir.config_parameter'].sudo().get_param('stock.no_negative_stock')
    #     )
    #     return res
    #

    # def set_values(self):
    #     super(ResConfigSettings, self).set_values()
    #     if not self.user_has_groups('stock.group_stock_manager'):
    #         return
    #     self.env['ir.config_parameter'].sudo().set_param('stock.no_negative_stock', self.no_negative_stock)
    #     self.env.user.company_id.write({'no_negative_stock': self.no_negative_stock})
