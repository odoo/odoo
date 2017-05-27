# -*- coding: utf-8 -*-
from openerp import api, models
from openerp.tools.translate import _


class AccountInvoice(models.Model):
    """ Printable account_invoice.
    """

    _name = 'account.invoice'
    _inherit = ['account.invoice', 'print.mixin']

    def print_validate_sending(self):
        super(AccountInvoice, self).print_validate_sending()
        PrintOrder = self.env['print.order']
        for record in self:
            order = PrintOrder.search([('res_model', '=', 'account.invoice'), ('res_id', '=', record.id)], limit=1, order='sent_date desc')
            if order:
                # put confirmation message in the chatter
                message = _("This invoice was sent by post with the provider %(provider_name)s at the following address. \
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
        # save sending data
        self.write({
            'sent' : True
        })

