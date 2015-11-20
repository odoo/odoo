# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp import SUPERUSER_ID


class sale_order(osv.Model):
    _inherit = 'sale.order'

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

    def action_confirm(self, cr, uid, ids, context=None):
        # fetch the partner's id and subscribe the partner to the sale order
        assert len(ids) == 1
        document = self.browse(cr, uid, ids[0], context=context)
        partner = document.partner_id
        if partner not in document.message_partner_ids:
            self.message_subscribe(cr, uid, ids, [partner.id], context=context)
        return super(sale_order, self).action_confirm(cr, uid, ids, context=context)

    def get_signup_url(self, cr, uid, ids, context=None):
        assert len(ids) == 1
        document = self.browse(cr, uid, ids[0], context=context)
        contex_signup = dict(context, signup_valid=True)
        return self.pool['res.partner']._get_signup_url_for_action(
            cr, uid, [document.partner_id.id], action='/mail/view',
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
            if partner not in invoice.message_partner_ids:
                self.message_subscribe(cr, uid, [invoice.id], [partner.id], context=context)
        return super(account_invoice, self).invoice_validate(cr, uid, ids, context=context)

    def get_signup_url(self, cr, uid, ids, context=None):
        assert len(ids) == 1
        document = self.browse(cr, uid, ids[0], context=context)
        contex_signup = dict(context, signup_valid=True)
        return self.pool['res.partner']._get_signup_url_for_action(
            cr, uid, [document.partner_id.id], action='/mail/view',
            model=self._name, res_id=document.id, context=contex_signup,
        )[document.partner_id.id]

    def get_formview_action(self, cr, uid, id, context=None):
        user = self.pool['res.users'].browse(cr, SUPERUSER_ID, uid, context=context)
        if user.share:
            return self.pool['ir.actions.act_window'].for_xml_id(cr, uid, 'portal_sale', 'portal_action_invoices', context=context)
        return super(account_invoice, self).get_formview_action(cr, uid, id, context=context)
