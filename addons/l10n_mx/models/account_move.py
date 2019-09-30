# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _move_autocomplete_invoice_lines_values(self):
        self._l10n_mx_get_import_tax_base_amount_lines()
        res = super(
            AccountMove, self)._move_autocomplete_invoice_lines_values()
        return res

    def _l10n_mx_get_import_tax_base_amount_lines(self):
        """Appends two lines for each one of the lines where the quantity is
        zero, as the value of the lines added are need in cash basis taxes to
        properly compute the taxes paid"""
        self.ensure_one()
        foreign = self.line_ids.mapped('l10n_mx_invoice_broker_id.partner_id')
        self.line_ids.filtered(
            lambda line: line.partner_id in foreign).unlink()
        aml_obj = self.env['account.move.line'].with_context(
            check_move_validity=False, recompute=False)

        lines_2_create = []
        for line in self.line_ids.filtered(
                lambda l: not l.quantity and l.tax_ids and
                l.l10n_mx_invoice_broker_id):
            if line.l10n_mx_invoice_broker_id == self:
                self.message_post(body=_(
                    'The Overseas Invoice cannot be the same that the'
                    'related invoice'))
                continue
            tax_ids = line.tax_ids | line.tax_ids.mapped(
                'children_tax_ids').filtered(
                    lambda child: child.type_tax_use != 'none')

            price = line.price_unit
            partner_id = line.l10n_mx_invoice_broker_id.\
                commercial_partner_id.id or self.commercial_partner_id.id
            move_line_dict = {
                'name': (line.name or '').split('\n')[0][:64],
                'move_id': line.move_id,
                'company_id': line.move_id.company_id.id,
                'account_id': line.account_id.id,
                'product_id': line.product_id.id,
                'tax_ids': [(6, 0, tax_ids.ids)],
                'partner_id': partner_id,
                'exclude_from_invoice_tab': True,
                'quantity': 1,
                'price_unit': abs(price),
                'price_total': abs(price),
                'price_subtotal': abs(price),
            }
            aml_obj.new(move_line_dict)

            price = -price

            ml_dict = dict(
                move_line_dict,
                tax_ids=[],
                price_unit=-abs(price),
                price_total=-abs(price),
                price_subtotal=-abs(price),
            )
            lines_2_create.append(ml_dict)

        for ml_dict in lines_2_create:
            aml_obj.new(ml_dict)
        return True


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_mx_invoice_broker_id = fields.Many2one(
        'account.move', string='Overseas Invoice',
        domain="[('type', '=', 'in_invoice'), ('state', '=', 'posted')]",
        help='This is the source invoice upon taxes are included in this line '
        'and that were paid by the broker on behalf of the company')
