# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp.tools.translate import _


class MailingListWizard(osv.TransientModel):
    """A wizard allowing to create an email.template from a mass mailing. This wizard
    allows to simplify and direct the user in the creation of its template without
    having to tune or hack the email.template model. """
    _name = 'mail.mass_mailing.list.create'
    _inherit = 'mail.mass_mailing.list'

    def action_new_list(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids[0], context=context)
        action_id = self.pool['mail.mass_mailing']._get_model_to_list_action_id(cr, uid, wizard.model, context=context)
        ctx = dict(context, search_default_not_opt_out=True, view_manager_highlight=[action_id], default_name=wizard.name, default_model=wizard.model)
        return {
            'name': _('Choose Recipients'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': wizard.model,
            'context': ctx,
        }
