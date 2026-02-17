from odoo import api, fields, models
#estate_property
import logging

_logger = logging.getLogger(__name__)
class estate_property(models.Model):
    _inherit ='estate.property'
    name2 = fields.Char()

    def sold_property(self):
        _logger.info("Starting sold_property for property: %s", self.name)
        super(estate_property, self).sold_property()

        account = self.env['account.account'].search([
            ('account_type', '=', 'income'),
            ('company_ids', 'in', self.env.company.id)
        ], limit=1)

        if not account:
            _logger.error("No income account found for company %s", self.env.company.id)
            raise ValueError("No income account found. Please configure an income account.")

        for record in self:
            if not record.buyer:
                _logger.warning("No buyer for property %s", record.name)
                continue
            if not record.Selling_Price:
                _logger.warning("No selling price for property %s", record.name)
                continue
            _logger.info("Creating invoice for buyer %s, selling price %s",
                         record.buyer.name, record.Selling_Price)
            self.env['account.move'].create({
                'partner_id': record.buyer.id,
                'move_type': 'out_invoice',
                'invoice_line_ids': [
                    (0, 0, {
                        'name': 'Property Sale',
                        'quantity': 1,
                        'price_unit': record.Selling_Price,
                        'account_id': account.id,
                    }),
                    (0, 0, {
                        'name': 'Administrative Fees',
                        'quantity': 1,
                        'price_unit': 100.0,
                        'account_id': account.id,
                    }),
                    (0, 0, {
                        'name': 'Tax of Property Sale',
                        'quantity': 1,
                        'price_unit': record.Selling_Price*0.06,
                        'account_id': account.id,
                    }),
                ]
            })
        _logger.info("sold_property completed for property: %s", self.name)
        return True

    def cancel_property(self):
        _logger.info("Canceling property: %s", self.name)
        return super().cancel_property()