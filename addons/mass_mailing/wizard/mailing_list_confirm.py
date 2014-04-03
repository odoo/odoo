# -*- coding: utf-8 -*-

from openerp.osv import osv, fields
from openerp.tools.translate import _


class MailingListConfirm(osv.TransientModel):
    """A wizard that acts as a confirmation when creating a new mailing list coming
    from a list view. This allows to have a lightweight flow to create mailing
    lists without having to go through multiple screens."""

    _inherit = 'mail.mass_mailing.list'
    _name = 'mail.mass_mailing.list.confirm'

    _columns = {
        'mass_mailing_id': fields.many2one('mail.mass_mailing', 'Mailing'),
    }

    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        context.update(no_contact_to_list=True)
        return super(MailingListConfirm, self).create(cr, uid, values, context=context)

    def action_confirm(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids[0], context=context)
        mailing_list_id = self.pool['mail.mass_mailing.list'].create(
            cr, uid, {'name': wizard.name, 'model': wizard.model}, context=context)
        res = self.pool['mail.mass_mailing.list'].action_add_to_mailing(cr, uid, [mailing_list_id], context=context)
        if not res:
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'mail.mass_mailing.list',
                'res_id': mailing_list_id,
                'context': context,
            }
        return res

    def action_new_list(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids[0], context=context)
        action_id = self.pool['mail.mass_mailing']._get_model_to_list_action_id(cr, uid, wizard.model, context=context)
        if wizard.model == 'mail.mass_mailing.contact':
            domain = [('list_id', '=', False)]
        else:
            domain = []
        ctx = dict(context, search_default_not_opt_out=True, view_manager_highlight=[action_id], default_name=wizard.name, default_model=wizard.model)
        return {
            'name': _('Choose Recipients'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': wizard.model,
            'context': ctx,
            'domain': domain,
        }
