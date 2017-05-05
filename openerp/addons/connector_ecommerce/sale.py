# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2011-2013 Camptocamp SA
#    Author: Sébastien Beau
#    Copyright 2010-2013 Akretion
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging

from openerp import models, fields, api, exceptions, _, osv
from openerp.addons.connector.connector import ConnectorUnit

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    """ Add a cancellation mecanism in the sales orders

    When a sales order is canceled in a backend, the connectors can flag
    the 'canceled_in_backend' flag. It will:

    * try to automatically cancel the sales order
    * block the confirmation of the sales orders using a 'sales exception'

    When a sales order is canceled or the user used the button to force
    to 'keep it open', the flag 'cancellation_resolved' is set to True.

    The second axe which can be used by the connectors is the 'parent'
    sales order. When a sales order has a parent sales order (logic to
    link with the parent to be defined by each connector), it will be
    blocked until the cancellation of the sales order is resolved.

    This is used by, for instance, the magento connector, when one
    modifies a sales order, Magento cancels it and create a new one with
    the first one as parent.
    """
    _inherit = 'sale.order'

    canceled_in_backend = fields.Boolean(string='Canceled in backend',
                                         readonly=True)
    # set to True when the cancellation from the backend is
    # resolved, either because the SO has been canceled or
    # because the user manually chose to keep it open
    cancellation_resolved = fields.Boolean(string='Cancellation from the '
                                                  'backend resolved')
    parent_id = fields.Many2one(comodel_name='sale.order',
                                compute='get_parent_id',
                                string='Parent Order',
                                help='A parent sales order is a sales '
                                     'order replaced by this one.')
    need_cancel = fields.Boolean(compute='_need_cancel',
                                 string='Need to be canceled',
                                 help='Has been canceled on the backend'
                                      ', need to be canceled.')
    parent_need_cancel = fields.Boolean(
        compute='_parent_need_cancel',
        string='A parent sales order needs cancel',
        help='A parent sales order has been canceled on the backend'
             ' and needs to be canceled.',
    )

    @api.one
    @api.depends()
    def get_parent_id(self):
        """ Need to be inherited in the connectors to implement the
        parent logic.

        See an implementation example in ``magentoerpconnect``.
        """
        self.parent_id = False

    @api.one
    @api.depends('canceled_in_backend', 'cancellation_resolved')
    def _need_cancel(self):
        """ Return True if the sales order need to be canceled
        (has been canceled on the Backend)
        """
        self.need_cancel = (self.canceled_in_backend and
                            not self.cancellation_resolved)

    @api.one
    @api.depends('need_cancel', 'parent_id',
                 'parent_id.need_cancel', 'parent_id.parent_need_cancel')
    def _parent_need_cancel(self):
        """ Return True if at least one parent sales order need to
        be canceled (has been canceled on the backend).
        Follows all the parent sales orders.
        """
        self.parent_need_cancel = False
        order = self.parent_id
        while order:
            if order.need_cancel:
                self.parent_need_cancel = True
            order = order.parent_id

    @api.multi
    def _try_auto_cancel(self):
        """ Try to automatically cancel a sales order canceled
        in a backend.

        If it can't cancel it, does nothing.
        """
        wkf_states = ('draft', 'sent')
        action_states = ('manual', 'progress')
        resolution_msg = _("<p>Resolution:<ol>"
                           "<li>Cancel the linked invoices, delivery "
                           "orders, automatic payments.</li>"
                           "<li>Cancel the sales order manually.</li>"
                           "</ol></p>")
        for order in self:
            state = order.state
            if state == 'cancel':
                continue
            elif state == 'done':
                message = _("The sales order cannot be automatically "
                            "canceled because it is already done.")
            elif state in wkf_states + action_states:
                try:
                    # respect the same cancellation methods than
                    # the sales order view: quotations use the workflow
                    # action, sales orders use the action_cancel method.
                    if state in wkf_states:
                        order.signal_workflow('cancel')
                    elif state in action_states:
                        order.action_cancel()
                    else:
                        raise ValueError('%s should not fall here.' % state)
                except (osv.osv.except_osv, osv.orm.except_orm,
                        exceptions.Warning):
                    # the 'cancellation_resolved' flag will stay to False
                    message = _("The sales order could not be automatically "
                                "canceled.") + resolution_msg
                else:
                    message = _("The sales order has been automatically "
                                "canceled.")
            else:
                # shipping_except, invoice_except, ...
                # can not be canceled from the view, so assume that it
                # should not be canceled here neiter, exception to
                # resolve
                message = _("The sales order could not be automatically "
                            "canceled for this status.") + resolution_msg
            order.message_post(body=message)

    @api.multi
    def _log_canceled_in_backend(self):
        message = _("The sales order has been canceled on the backend.")
        self.message_post(body=message)
        for order in self:
            message = _("Warning: the origin sales order %s has been canceled "
                        "on the backend.") % order.name
            if order.picking_ids:
                order.picking_ids.message_post(body=message)
            if order.invoice_ids:
                order.invoice_ids.message_post(body=message)

    @api.model
    def create(self, values):
        order = super(SaleOrder, self).create(values)
        if values.get('canceled_in_backend'):
            order._log_canceled_in_backend()
            order._try_auto_cancel()
        return order

    @api.multi
    def write(self, values):
        result = super(SaleOrder, self).write(values)
        if values.get('canceled_in_backend'):
            self._log_canceled_in_backend()
            self._try_auto_cancel()
        return result

    @api.multi
    def action_cancel(self):
        res = super(SaleOrder, self).action_cancel()
        for sale in self:
            # the sales order is canceled => considered as resolved
            if (sale.canceled_in_backend and
                    not sale.cancellation_resolved):
                sale.write({'cancellation_resolved': True})
        return res

    @api.multi
    def ignore_cancellation(self, reason):
        """ Manually set the cancellation from the backend as resolved.

        The user can choose to keep the sales order active for some reason,
        it only requires to push a button to keep it alive.
        """
        message = (_("Despite the cancellation of the sales order on the "
                     "backend, it should stay open.<br/><br/>Reason: %s") %
                   reason)
        self.message_post(body=message)
        self.write({'cancellation_resolved': True})
        return True

    @api.multi
    def action_view_parent(self):
        """ Return an action to display the parent sales order """
        self.ensure_one()

        parent = self.parent_id
        if not parent:
            return

        view_xmlid = 'sale.view_order_form'
        if parent.state in ('draft', 'sent', 'cancel'):
            action_xmlid = 'sale.action_quotations'
        else:
            action_xmlid = 'sale.action_orders'

        action = self.env.ref(action_xmlid).read()[0]

        view = self.env.ref(view_xmlid)
        action['views'] = [(view.id if view else False, 'form')]
        action['res_id'] = parent.id
        return action


class SpecialOrderLineBuilder(ConnectorUnit):
    """ Base class to build a sales order line for a sales order

    Used when extra order lines have to be added in a sales order
    but we only know some parameters (product, price, ...), for instance,
    a line for the shipping costs or the gift coupons.

    It can be subclassed to customize the way the lines are created.

    Usage::

        builder = self.get_connector_for_unit(ShippingLineBuilder,
                                              model='sale.order.line')
        builder.price_unit = 100
        builder.get_line()

    """
    _model_name = None

    def __init__(self, connector_env):
        super(SpecialOrderLineBuilder, self).__init__(connector_env)
        self.product = None  # id or browse_record
        # when no product_id, fallback to a product_ref
        self.product_ref = None  # tuple (module, xmlid)
        self.price_unit = None
        self.quantity = 1
        self.sign = 1
        self.sequence = 980

    def get_line(self):
        assert self.product_ref or self.product
        assert self.price_unit is not None

        product = self.product
        if product is None:
            product = self.env.ref('.'.join(self.product_ref))

        if not isinstance(product, models.BaseModel):
            product = self.env['product.product'].browse(product)
        return {'product_id': product.id,
                'name': product.name,
                'product_uom': product.uom_id.id,
                'product_uom_qty': self.quantity,
                'price_unit': self.price_unit * self.sign,
                'sequence': self.sequence}


class ShippingLineBuilder(SpecialOrderLineBuilder):
    """ Return values for a Shipping line """
    _model_name = None

    def __init__(self, connector_env):
        super(ShippingLineBuilder, self).__init__(connector_env)
        self.product_ref = ('connector_ecommerce', 'product_product_shipping')
        self.sequence = 999


class CashOnDeliveryLineBuilder(SpecialOrderLineBuilder):
    """ Return values for a Cash on Delivery line """
    _model_name = None
    _model_name = None

    def __init__(self, connector_env):
        super(CashOnDeliveryLineBuilder, self).__init__(connector_env)
        self.product_ref = ('connector_ecommerce',
                            'product_product_cash_on_delivery')
        self.sequence = 995


class GiftOrderLineBuilder(SpecialOrderLineBuilder):
    """ Return values for a Gift line """
    _model_name = None

    def __init__(self, connector_env):
        super(GiftOrderLineBuilder, self).__init__(connector_env)
        self.product_ref = ('connector_ecommerce',
                            'product_product_gift')
        self.sign = -1
        self.gift_code = None
        self.sequence = 990

    def get_line(self):
        line = super(GiftOrderLineBuilder, self).get_line()
        if self.gift_code:
            line['name'] = "%s [%s]" % (line['name'], self.gift_code)
        return line
