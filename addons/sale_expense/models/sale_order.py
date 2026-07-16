# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    expense_ids = fields.One2many(
        comodel_name='hr.expense',
        inverse_name='sale_order_id',
        string='Expenses',
        readonly=True,
    )
    expense_count = fields.Integer("# of Expenses", compute='_compute_expense_count', compute_sudo=True)
    is_linked_to_expense_with_attachment = fields.Boolean(compute='_compute_is_linked_to_expense_with_attachment')

    def _compute_is_linked_to_expense_with_attachment(self):
        order_attachments_map = self._get_expense_attachments_not_linked_yet()
        for order in self:
            order.is_linked_to_expense_with_attachment = order_attachments_map.get(order, [])

    def _get_expense_attachments_not_linked_yet(self):
        """
        Returns a dict specifying expense attachments that are not linked yet with the sale order(s) in self

        :return: A dict that maps orders to their not yet linked attachments
        :rtype: dict
        """
        checksums = dict(self.env['ir.attachment']._read_group([
            ('res_model', 'in', self._name),
            ('res_id', 'in', self.ids),
        ], groupby=['res_id'], aggregates=['checksum:array_agg']))
        return {
            order: order.expense_ids.attachment_ids.filtered(lambda a: a.checksum not in checksums.get(order.id, []))
            for order in self
        }

    @api.model
    def _search_display_name(self, operator, value):
        """ For expense, we want to show all sales order but only their display_name (no ir.rule applied), this is the only way to do it. """
        if (
            self.env.context.get('sale_expense_all_order')
            and self.env.user.has_group('sales_team.group_sale_salesman')
            and not self.env.user.has_group('sales_team.group_sale_salesman_all_leads')
        ):
            if operator in Domain.NEGATIVE_OPERATORS:
                return NotImplemented
            domain = super()._search_display_name(operator, value)
            company_domain = Domain('state', '=', 'sale') & Domain('company_id', 'in', self.env.companies.ids)
            query = self.sudo()._search(domain & company_domain)
            return Domain('id', 'in', query)
        return super()._search_display_name(operator, value)

    @api.depends('expense_ids')
    def _compute_expense_count(self):
        expense_data = self.env['hr.expense']._read_group(
            domain=[('sale_order_id', 'in', self.ids)],
            groupby=['sale_order_id'],
            aggregates=['__count'])
        mapped_data = {sale_order.id: count for sale_order, count in expense_data}
        for sale_order in self:
            sale_order.expense_count = mapped_data.get(sale_order.id, 0)

    def action_copy_reinvoiced_expense_receipts(self):
        self.ensure_one()
        if not self.expense_ids.attachment_ids:
            raise UserError(self.env._("No attachment found to import from linked expense(s)"))

        wizard = self.env['expense.attachment.selection.wizard'].create({
            'sale_order_id': self.id,
        })
        return wizard._get_records_action(name=self.env._("Attachments Selection"), target='new')
