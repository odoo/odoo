from odoo import fields, models

class Lead(models.Model):
    _inherit = 'crm.lead'

    def website_form_input_filter(self, request, values):
        values.update({
            'medium_id': values.get('medium_id') or self.default_get(['medium_id']).get('medium_id') or
            self.sudo().env.ref('utm.utm_medium_website').id,
            'team_id': request.website.salesteam_id.id
            }
        )
        return values

class CrmTeam(models.Model):
    _inherit = "crm.team"

    website_ids = fields.One2many('website', 'salesteam_id', string='Websites', help="Websites using this sales team")
