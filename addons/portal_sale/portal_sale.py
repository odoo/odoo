# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2012 OpenERP S.A. <http://openerp.com>
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

from openerp.osv import osv, fields


class sale_order(osv.Model):
    _inherit = 'sale.order'

    # make the real method inheritable
    _payment_block_proxy = lambda self, *a, **kw: self._portal_payment_block(*a, **kw)

    _columns = {
        'portal_payment_options': fields.function(_payment_block_proxy, type="html", string="Portal Payment Options"),
    }

    def _portal_payment_block(self, cr, uid, ids, fieldname, arg, context=None):
        result = dict.fromkeys(ids, False)
        payment_acquirer = self.pool.get('portal.payment.acquirer')
        for this in self.browse(cr, uid, ids, context=context):
            if this.state not in ('draft', 'cancel') and not this.invoiced:
                result[this.id] = payment_acquirer.render_payment_block(cr, uid, this, this.name,
                    this.pricelist_id.currency_id, this.amount_total, context=context)
        return result

    def action_quotation_send(self, cr, uid, ids, context=None):
        '''  Override to use a modified template that includes a portal signup link '''
        action_dict = super(sale_order, self).action_quotation_send(cr, uid, ids, context=context)
        try:
            template_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'portal_sale', 'email_template_edi_sale')[1]
            # assume context is still a dict, as prepared by super
            ctx = action_dict['context']
            ctx['default_template_id'] = template_id
            ctx['default_use_template'] = True
        except Exception:
            pass
        return action_dict

    def action_button_confirm(self, cr, uid, ids, context=None):
        # fetch the partner's id and subscribe the partner to the sale order
        assert len(ids) == 1
        document = self.browse(cr, uid, ids[0], context=context)
        partner = document.partner_id
        if partner.id not in document.message_follower_ids:
            self.message_subscribe(cr, uid, ids, [partner.id], context=context)
            user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
            mail_values = {
                'email_from': user.partner_id.email,
                'email_to': partner.email,
                'subject': 'Invitation to follow %s' % document.name_get()[0][1],
                'body_html': 'You have been invited to follow %s' % document.name_get()[0][1],
                'auto_delete': True,
                'type': 'email',
            }
            mail_obj = self.pool.get('mail.mail')
            mail_id = mail_obj.create(cr, uid, mail_values, context=context)
            mail_obj.send(cr, uid, [mail_id], recipient_ids=[partner.id], context=context)
        return super(sale_order, self).action_button_confirm(cr, uid, ids, context=context)

    def get_signup_url(self, cr, uid, ids, context=None):
        assert len(ids) == 1
        document = self.browse(cr, uid, ids[0], context=context)
        partner = document.partner_id
        action = 'portal_sale.action_quotations_portal' if document.state in ('draft', 'sent') else 'portal_sale.action_orders_portal'
        partner.signup_prepare()
        return partner._get_signup_url_for_action(action=action, view_type='form', res_id=document.id)[partner.id]


class account_invoice(osv.Model):
    _inherit = 'account.invoice'

    # make the real method inheritable
    _payment_block_proxy = lambda self, *a, **kw: self._portal_payment_block(*a, **kw)

    _columns = {
        'portal_payment_options': fields.function(_payment_block_proxy, type="html", string="Portal Payment Options"),
    }

    def _portal_payment_block(self, cr, uid, ids, fieldname, arg, context=None):
        result = dict.fromkeys(ids, False)
        payment_acquirer = self.pool.get('portal.payment.acquirer')
        for this in self.browse(cr, uid, ids, context=context):
            if this.type == 'out_invoice' and this.state not in ('draft', 'done') and not this.reconciled:
                result[this.id] = payment_acquirer.render_payment_block(cr, uid, this, this.number,
                    this.currency_id, this.residual, context=context)
        return result

    def action_invoice_sent(self, cr, uid, ids, context=None):
        '''  Override to use a modified template that includes a portal signup link '''
        action_dict = super(account_invoice, self).action_invoice_sent(cr, uid, ids, context=context)
        try:
            template_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'portal_sale', 'email_template_edi_invoice')[1]
            # assume context is still a dict, as prepared by super
            ctx = action_dict['context']
            ctx['default_template_id'] = template_id
            ctx['default_use_template'] = True
        except Exception:
            pass
        return action_dict

    def invoice_validate(self, cr, uid, ids, context=None):
        # fetch the partner's id and subscribe the partner to the invoice
        document = self.browse(cr, uid, ids[0], context=context)
        partner = document.partner_id
        if partner.id not in document.message_follower_ids:
            self.message_subscribe(cr, uid, ids, [partner.id], context=context)
            user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
            mail_values = {
                'email_from': user.partner_id.email,
                'email_to': partner.email,
                'subject': 'Invitation to follow %s' % document.name_get()[0][1],
                'body_html': 'You have been invited to follow %s' % document.name_get()[0][1],
                'auto_delete': True,
                'type': 'email',
            }
            mail_obj = self.pool.get('mail.mail')
            mail_id = mail_obj.create(cr, uid, mail_values, context=context)
            mail_obj.send(cr, uid, [mail_id], recipient_ids=[partner.id], context=context)
        return super(account_invoice, self).invoice_validate(cr, uid, ids, context=context)

    def get_signup_url(self, cr, uid, ids, context=None):
        assert len(ids) == 1
        document = self.browse(cr, uid, ids[0], context=context)
        partner = document.partner_id
        action = 'portal_sale.portal_action_invoices'
        partner.signup_prepare()
        return partner._get_signup_url_for_action(action=action, view_type='form', res_id=document.id)[partner.id]


class mail_mail(osv.osv):
    _inherit = 'mail.mail'

    def _postprocess_sent_message(self, cr, uid, mail, context=None):
        if mail.model == 'sale.order':
            so_obj = self.pool.get('sale.order')
            order = so_obj.browse(cr, uid, mail.res_id, context=context)
            partner = order.partner_id
            # Add the customer in the SO as follower
            if partner.id not in order.message_follower_ids:
                so_obj.message_subscribe(cr, uid, [mail.res_id], [partner.id], context=context)
            # Add all recipients of the email as followers
            for p in mail.partner_ids:
                if p.id not in order.message_follower_ids:
                    so_obj.message_subscribe(cr, uid, [mail.res_id], [p.id], context=context)
        return super(mail_mail, self)._postprocess_sent_message(cr, uid, mail=mail, context=context)
