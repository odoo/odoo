# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from openerp.osv import osv, fields

from openerp.tools.translate import _


class MailMassMailingCreate(osv.TransientModel):
    """Wizard to help creating mass mailing waves for a campaign. """

    _name = 'mail.mass_mailing.create'
    _description = 'Mass mailing creation'

    _columns = {
        'mass_mailing_campaign_id': fields.many2one(
            'mail.mass_mailing.campaign', 'Mass mailing campaign',
            required=True,
        ),
        'model_id': fields.many2one(
            'ir.model', 'Document Type',
            required=True,
            help='Document on which the mass mailing will run. This must be a '
                 'valid OpenERP model.',
        ),
        'model_model': fields.related(
            'model_id', 'name',
            type='char', string='Model Name'
        ),
        'filter_id': fields.many2one(
            'ir.filters', 'Filter',
            required=True,
            domain="[('model_id', '=', model_model)]",
            help='Filter to be applied on the document to find the records to be '
                 'mailed.',
        ),
        'domain': fields.related(
            'filter_id', 'domain',
            type='char', string='Domain',
        ),
        'template_id': fields.many2one(
            'email.template', 'Template', required=True,
            domain="[('model_id', '=', model_id)]",
        ),
        'name': fields.char(
            'Mailing Name', required=True,
            help='Name of the mass mailing.',
        ),
        'mass_mailing_id': fields.many2one(
            'mail.mass_mailing', 'Mass Mailing',
        ),
    }

    def _get_default_model_id(self, cr, uid, context=None):
        model_ids = self.pool['ir.model'].search(cr, uid, [('model', '=', 'res.partner')], context=context)
        return model_ids and model_ids[0] or False

    _defaults = {
        'model_id': lambda self, cr, uid, ctx=None: self._get_default_model_id(cr, uid, context=ctx),
    }

    def on_change_model_id(self, cr, uid, ids, model_id, context=None):
        if model_id:
            model_model = self.pool['ir.model'].browse(cr, uid, model_id, context=context).model
        else:
            model_model = False
        return {'value': {'model_model': model_model}}

    def on_change_filter_id(self, cr, uid, ids, filter_id, context=None):
        if filter_id:
            domain = self.pool['ir.filters'].browse(cr, uid, filter_id, context=context).domain
        else:
            domain = False
        return {'value': {'domain': domain}}

    def create_mass_mailing(self, cr, uid, ids, context=None):
        """ Create a mass mailing based on wizard data, and update the wizard """
        for wizard in self.browse(cr, uid, ids, context=context):
            mass_mailing_values = {
                'name': wizard.name,
                'mass_mailing_campaign_id': wizard.mass_mailing_campaign_id.id,
                'domain': wizard.domain,
                'template_id': wizard.template_id.id,
            }
            mass_mailing_id = self.pool['mail.mass_mailing'].create(cr, uid, mass_mailing_values, context=context)
            self.write(cr, uid, [wizard.id], {'mass_mailing_id': mass_mailing_id}, context=context)
        return True

    def launch_composer(self, cr, uid, ids, context=None):
        """ Main wizard action: create a new mailing and launch the mail.compose.message
        email composer with wizard data. """
        self.create_mass_mailing(cr, uid, ids, context=context)

        wizard = self.browse(cr, uid, ids[0], context=context)
        ctx = dict(context)
        ctx.update({
            'default_composition_mode': 'mass_mail',
            'default_template_id': wizard.template_id.id,
            'default_use_mass_mailing_campaign': True,
            'default_use_active_domain': True,
            'default_model': wizard.model_id.model,
            'default_res_id': False,
            'default_active_domain': wizard.domain,
            'default_mass_mailing_campaign_id': wizard.mass_mailing_campaign_id.id,
            'default_mass_mailing_id': wizard.mass_mailing_id.id,
        })
        return {
            'name': _('Compose Email for Mass Mailing'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }
