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


class MailMassMailingSegmentCreate(osv.TransientModel):
    """Wizard to help creating mass mailing segments for a campaign. """

    _name = 'mail.mass_mailing.segment.create'
    _description = 'Mass mailing segment creation'

    _columns = {
        'mass_mailing_campaign_id': fields.many2one(
            'mail.mass_mailing.campaign', 'Mass mailing campaign',
            required=True,
        ),
        'model_id': fields.many2one(
            'ir.model', 'Model',
            required=True,
        ),
        'model_model': fields.related(
            'model_id', 'name',
            type='char', string='Model Name'
        ),
        'filter_id': fields.many2one(
            'ir.filters', 'Filter',
            domain="[('model_id', '=', model_model)]",
        ),
        'domain': fields.related(
            'filter_id', 'domain',
            type='char', string='Domain',
        ),
        'template_id': fields.many2one(
            'email.template', 'Template', required=True,
            domain="[('model_id', '=', model_id)]",
        ),
        'segment_name': fields.char(
            'Segment name', required=True,
        ),
        'mass_mailing_segment_id': fields.many2one(
            'mail.mass_mailing.segment', 'Mass Mailing Segment',
        ),
    }

    _defaults = {
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

    def create_segment(self, cr, uid, ids, context=None):
        """ Create a segment based on wizard data, and update the wizard """
        for wizard in self.browse(cr, uid, ids, context=context):
            segment_values = {
                'name': wizard.segment_name,
                'mass_mailing_campaign_id': wizard.mass_mailing_campaign_id.id,
                'domain': wizard.domain,
                'template_id': wizard.template_id.id,
            }
            segment_id = self.pool['mail.mass_mailing.segment'].create(cr, uid, segment_values, context=context)
            self.write(cr, uid, [wizard.id], {'mass_mailing_segment_id': segment_id}, context=context)
        return True

    def launch_composer(self, cr, uid, ids, context=None):
        """ Main wizard action: create a new segment and launch the mail.compose.message
        email composer with wizard data. """
        self.create_segment(cr, uid, ids, context=context)

        wizard = self.browse(cr, uid, ids[0], context=context)
        ctx = dict(context)
        ctx.update({
            'default_composition_mode': 'mass_mail',
            'default_template_id': wizard.template_id.id,
            'default_use_mass_mailing_campaign': True,
            'default_use_active_domain': True,
            'default_active_domain': wizard.domain,
            'default_mass_mailing_campaign_id': wizard.mass_mailing_campaign_id.id,
            'default_mass_mailing_segment_id': wizard.mass_mailing_segment_id.id,
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
