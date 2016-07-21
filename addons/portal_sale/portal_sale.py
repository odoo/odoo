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

from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp import SUPERUSER_ID


class sale_order(osv.Model):
    _inherit = 'sale.order'

    # make the real method inheritable
    _payment_block_proxy = lambda self, *a, **kw: self._portal_payment_block(*a, **kw)

    _columns = {
        'portal_payment_options': fields.function(_payment_block_proxy, type="html", string="Portal Payment Options"),
    }

    def _portal_payment_block(self, cr, uid, ids, fieldname, arg, context=None):
        result = dict.fromkeys(ids, False)
        payment_acquirer = self.pool['payment.acquirer']
        for this in self.browse(cr, SUPERUSER_ID, ids, context=context):
            if this.state not in ('draft', 'cancel') and not this.invoiced:
                result[this.id] = payment_acquirer.render_payment_block(
                    cr, SUPERUSER_ID, this.name, this.amount_total, this.pricelist_id.currency_id.id,
                    partner_id=this.partner_id.id, company_id=this.company_id.id, context=context)
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
        if partner not in document.message_follower_ids:
            self.message_subscribe(cr, uid, ids, [partner.id], context=context)
        return super(sale_order, self).action_button_confirm(cr, uid, ids, context=context)

    def get_signup_url(self, cr, uid, ids, context=None):
        assert len(ids) == 1
        document = self.browse(cr, uid, ids[0], context=context)
        contex_signup = dict(context, signup_valid=True)
        return self.pool['res.partner']._get_signup_url_for_action(
            cr, uid, [document.partner_id.id], action='mail.action_mail_redirect',
            model=self._name, res_id=document.id, context=contex_signup,
        )[document.partner_id.id]

    def get_formview_action(self, cr, uid, id, context=None):
        user = self.pool['res.users'].browse(cr, SUPERUSER_ID, uid, context=context)
        if user.share:
            document = self.browse(cr, uid, id, context=context)
            action_xmlid = 'action_quotations_portal' if document.state in ('draft', 'sent') else 'action_orders_portal'
            return self.pool['ir.actions.act_window'].for_xml_id(cr, uid, 'portal_sale', action_xmlid, context=context)
        return super(sale_order, self).get_formview_action(cr, uid, id, context=context)


class account_invoice(osv.Model):
    _inherit = 'account.invoice'

    # make the real method inheritable
    _payment_block_proxy = lambda self, *a, **kw: self._portal_payment_block(*a, **kw)

    _columns = {
        'portal_payment_options': fields.function(_payment_block_proxy, type="html", string="Portal Payment Options"),
    }

    def _portal_payment_block(self, cr, uid, ids, fieldname, arg, context=None):
        result = dict.fromkeys(ids, False)
        payment_acquirer = self.pool.get('payment.acquirer')
        for this in self.browse(cr, uid, ids, context=context):
            if this.type == 'out_invoice' and this.state not in ('draft', 'done') and not this.reconciled:
                result[this.id] = payment_acquirer.render_payment_block(
                    cr, SUPERUSER_ID, this.number, this.residual, this.currency_id.id,
                    partner_id=this.partner_id.id, company_id=this.company_id.id, context=context)
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
        for invoice in self.browse(cr, uid, ids, context=context):
            partner = invoice.partner_id
            if partner not in invoice.message_follower_ids:
                self.message_subscribe(cr, uid, [invoice.id], [partner.id], context=context)
        return super(account_invoice, self).invoice_validate(cr, uid, ids, context=context)

    def get_signup_url(self, cr, uid, ids, context=None):
        assert len(ids) == 1
        document = self.browse(cr, uid, ids[0], context=context)
        contex_signup = dict(context, signup_valid=True)
        return self.pool['res.partner']._get_signup_url_for_action(
            cr, uid, [document.partner_id.id], action='mail.action_mail_redirect',
            model=self._name, res_id=document.id, context=contex_signup,
        )[document.partner_id.id]

    def get_formview_action(self, cr, uid, id, context=None):
        user = self.pool['res.users'].browse(cr, SUPERUSER_ID, uid, context=context)
        if user.share:
            return self.pool['ir.actions.act_window'].for_xml_id(cr, uid, 'portal_sale', 'portal_action_invoices', context=context)
        return super(account_invoice, self).get_formview_action(cr, uid, id, context=context)


class mail_mail(osv.osv):
    _inherit = 'mail.mail'

    def _postprocess_sent_message(self, cr, uid, mail, context=None, mail_sent=True):
        if mail_sent and mail.model == 'sale.order':
            so_obj = self.pool.get('sale.order')
            order = so_obj.browse(cr, uid, mail.res_id, context=context)
            partner = order.partner_id
            # Add the customer in the SO as follower
            if partner not in order.message_follower_ids:
                so_obj.message_subscribe(cr, uid, [mail.res_id], [partner.id], context=context)
            # Add all recipients of the email as followers
            for p in mail.partner_ids:
                if p not in order.message_follower_ids:
                    so_obj.message_subscribe(cr, uid, [mail.res_id], [p.id], context=context)
        return super(mail_mail, self)._postprocess_sent_message(cr, uid, mail=mail, context=context, mail_sent=mail_sent)
