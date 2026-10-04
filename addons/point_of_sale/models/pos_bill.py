from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PosBill(models.Model):
    _name = 'pos.bill'
    _order = "value"
    _description = "Coin/Bill"
    _inherit = ["pos.load.mixin"]

    def _default_available_currencies(self):
        return self.env.companies.mapped('currency_id')

    name = fields.Char("Name", required=True)
    value = fields.Float("Value", required=True, digits=(16, 4))
    pos_config_ids = fields.Many2many("pos.config", string="Point of Sales")
    available_currency_ids = fields.Many2many("res.currency", string="Currencies", default=_default_available_currencies)
    company_ids = fields.Many2many(
        "res.company", compute="_compute_company_ids", search="_search_company_ids",
    )

    def _compute_company_ids(self):
        for bill in self:
            bill.company_ids = self.env["res.company"].search(
                [("currency_id", "in", bill.available_currency_ids.ids)]
            )

    def _search_company_ids(self, operator, value):
        if operator != "in":
            return NotImplemented
        companies = self.env["res.company"].browse(value)
        return [("available_currency_ids", "in", companies.currency_id.ids)]

    @api.constrains('value')
    def _check_value_not_zero(self):
        for bill in self:
            if bill.value <= 0:
                raise ValidationError(_("The value of a coin/bill must be greater than 0."))

    @api.model
    def _load_pos_data_domain(self, data):
        config = data["pos.session"].config_id
        currency_ids = (
            config.company_id.currency_id
            | config.currency_id
            | config.payment_method_ids.currency_ids
        ).ids
        return [("available_currency_ids", "in", currency_ids)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'value']
