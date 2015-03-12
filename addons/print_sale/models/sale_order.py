# -*- coding: utf-8 -*-
from openerp import api, models
from openerp.tools.translate import _


class SaleOrder(models.Model):
    """ Printable sale_order """

    _name = 'sale.order'
    _inherit = ['sale.order', 'print.mixin']

    def print_validate_sending(self):
        PrintOrder = self.env['print.order']
        for record in self:
            order = PrintOrder.search([('res_model', '=', 'sale.order'), ('res_id', '=', record.id)], limit=1, order='sent_date desc')
            # put confirmation message in the chatter
            message = _("This sale order was sent by post with the provider %(provider_name)s at the following address. \
                    <br/><br/> %(partner_name)s <br/> %(partner_street)s <br/> %(partner_city)s %(partner_zip)s \
                    <br/>%(partner_country)s" % {
                        'provider_name' : '<i>%s</i>' % order.provider_id.name,
                        'partner_name' : order.partner_name,
                        'partner_street' : order.partner_street,
                        'partner_city' : order.partner_city,
                        'partner_zip' : order.partner_zip,
                        'partner_country' : order.partner_country_id.name
                    })
            record.sudo(user=order.user_id.id).message_post(body=message)

        super(SaleOrder, self).print_validate_sending()

        # make the transition to the sent state
        self.signal_workflow('quotation_sent')

