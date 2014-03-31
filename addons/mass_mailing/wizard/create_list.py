# -*- coding: utf-8 -*-

from openerp.osv import osv, fields
from openerp.tools.translate import _


class MailingListWizard(osv.TransientModel):
    """A wizard allowing to create an email.template from a mass mailing. This wizard
    allows to simplify and direct the user in the creation of its template without
    having to tune or hack the email.template model. """
    _name = 'mail.mass_mailing.list.create'

    def _get_model_list(self, cr, uid, context=None):
        return self.pool['mail.mass_mailing']._get_mailing_model(cr, uid, context=context)

    # indirections for inheritance
    _model_list = lambda self, *args, **kwargs: self._get_model_list(*args, **kwargs)

    _columns = {
        'name': fields.char('Name', required=True),
        'model': fields.selection(
            _model_list, type='char', required=True,
            string='Applies To'
        ),
    }

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
