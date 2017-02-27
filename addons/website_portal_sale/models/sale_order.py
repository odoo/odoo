# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, fields, models


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    website_url = fields.Char('Website URL', compute='_website_url', help='The full URL to access the document through the website.')

    def _website_url(self):
        for so in self:
            so.website_url = '/my/orders/%s' % (so.id)

    @api.multi
    def get_access_action(self):
        """ Instead of the classic form view, redirect to the online quote for
        portal users that have access to a confirmed order. """
        # TDE note: read access on sales order to portal users granted to followed sales orders
        self.ensure_one()
        if self.state == 'cancel' or (self.state == 'draft' and not self.env.context.get('mark_so_as_sent')):
            return super(SaleOrder, self).get_access_action()
        if self.env.user.share or self.env.context.get('force_website'):
            try:
                self.check_access_rule('read')
            except exceptions.AccessError:
                pass
            else:
                return {
                    'type': 'ir.actions.act_url',
                    'url': '/my/orders/%s' % self.id,
                    'target': 'self',
                    'res_id': self.id,
                }
        return super(SaleOrder, self).get_access_action()

    @api.multi
    def _notification_recipients(self, message, groups):
        groups = super(SaleOrder, self)._notification_recipients(message, groups)

        self.ensure_one()
        if self.state not in ('draft', 'cancel'):
            for group_name, group_method, group_data in groups:
                group_data['has_button_access'] = True

        return groups

    def _force_lines_to_invoice_policy_order(self):
        for line in self.order_line:
            if self.state in ['sale', 'done']:
                line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
            else:
                line.qty_to_invoice = 0

    @api.multi
    def get_signup_url(self):
        self.ensure_one()
        return self.partner_id.with_context(signup_valid=True)._get_signup_url_for_action(
            action='/mail/view',
            model=self._name,
            res_id=self.id)[self.partner_id.id]


class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'

    # Non-stored related field to allow portal user to see the image of the product he has ordered
    product_image = fields.Binary('Product Image', related="product_id.image", store=False)
