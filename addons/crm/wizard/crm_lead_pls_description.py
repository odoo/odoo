# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _
from odoo.tools.misc import get_field_value_string


class LeadPlsDescriptionField(models.TransientModel):
    _name = 'crm.lead.pls.description.field'
    _description = 'Information of the field used in the PLS calculation'

    lead_pls_description_id = fields.Many2one('crm.lead.pls.description', readonly=True)

    name = fields.Char('Field', readonly=True)
    value = fields.Char('Value', readonly=True)

    winning = fields.Boolean('Winning', help='This field/value increase the global score')


class LeadPlsDescription(models.TransientModel):
    _name = 'crm.lead.pls.description'
    _description = 'Description of the PLS calculation'

    lead_id = fields.Many2one('crm.lead', readonly=True)
    lead_fields = fields.One2many('crm.lead.pls.description.field', 'lead_pls_description_id', readonly=True)

    @api.model
    def default_get(self, fields):
        result = super(LeadPlsDescription, self).default_get(fields)
        current_lead = self.env['crm.lead'].browse(self._context.get('active_ids'))

        if not current_lead.team_id:
            raise UserError(_('The lead need a sale team'))

        lead_info = current_lead._pls_get_statistics().get(current_lead.id)

        if not lead_info:
            raise UserError(_('Cannot retrieve statistics about the lead'))

        if not lead_info.get('statistics'):
            raise UserError(_('No description are available'))

        avg_score = (sum((won / won_total) / (won / won_total + lost / lost_total)
                         for *_, won, won_total, lost, lost_total in lead_info['statistics'])
                     / len(lead_info['statistics']))

        result.update({
            'lead_id': current_lead.id,
            'lead_fields': sorted([
                (0, 0, {'name': _('Tags') if field_name == 'tag_id' else self.env['crm.lead']._fields[field_name].string,
                        'value': get_field_value_string(self.env['crm.lead'], 'tag_ids' if field_name == 'tag_id' else field_name, field_value, self.env),
                        'winning': ((won / won_total) / (won / won_total + lost / lost_total)) >= avg_score
                        })
                for field_name, field_value, won, won_total, lost, lost_total in lead_info['statistics']
            ], key=lambda r: r[2]['winning'], reverse=True)
        })

        return result
