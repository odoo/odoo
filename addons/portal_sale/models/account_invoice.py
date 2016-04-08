# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import SUPERUSER_ID
from openerp.osv import osv
from openerp import SUPERUSER_ID


class account_invoice(osv.Model):
    _inherit = 'account.invoice'

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
        context = context or {}
        user = self.pool['res.users'].browse(cr, SUPERUSER_ID, context.get('uid', uid), context=context)
        if user.share:
            return self.pool['ir.actions.act_window'].for_xml_id(cr, uid, 'portal_sale', 'portal_action_invoices', context=context)
        return super(account_invoice, self).get_formview_action(cr, uid, id, context=context)
