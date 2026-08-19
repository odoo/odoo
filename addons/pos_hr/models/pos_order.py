# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    employee_id = fields.Many2one('hr.employee', string="Cashier", help="The employee who uses the cash register.")
    cashier = fields.Char(string="Cashier name", compute="_compute_cashier", store=True)

    @api.depends('employee_id', 'user_id')
    def _compute_cashier(self):
        for order in self:
            if order.employee_id:
                order.cashier = order.employee_id.name
            else:
                order.cashier = order.user_id.name

    def write(self, vals):
        # Set the author of tracked-field chatter entries to the employee selected in the PoS UI
        for order in self:
            order._track_set_log_author(order._get_message_author())
        return super().write(vals)

    def _get_message_author(self):
        """Return the cashier responsible for the order as the chatter author."""
        self.ensure_one()
        cashier = self.env['hr.employee']._get_current_cashier()
        employee = cashier or self.session_id.employee_id or self.employee_id
        return employee._get_pos_message_author() or super()._get_message_author()

    def message_post(self, **kwargs):
        # Only use the cashier when the request comes from the PoS, so that a
        # message written from the backend keeps the user who wrote it as author.
        cashier = self.env['hr.employee']._get_current_cashier()
        if not kwargs.get('author_id') and (author := cashier._get_pos_message_author()):
            kwargs['author_id'] = author.id
        return super().message_post(**kwargs)

    def _message_log_batch(self, bodies, subject=False, author_id=None, email_from=None,
                           message_type='notification', partner_ids=False,
                           attachment_ids=False, tracking_values=False):
        # The ORM posts the creation log without an author. Since all messages in
        # the batch share a single author, only use the current cashier here rather
        # than the per-record fallbacks from `_get_message_author`.
        cashier = self.env['hr.employee']._get_current_cashier()
        if not author_id and (author := cashier._get_pos_message_author()):
            author_id = author.id
        return super()._message_log_batch(
            bodies, subject=subject, author_id=author_id, email_from=email_from,
            message_type=message_type, partner_ids=partner_ids,
            attachment_ids=attachment_ids, tracking_values=tracking_values,
        )
