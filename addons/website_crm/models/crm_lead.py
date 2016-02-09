from openerp import models, SUPERUSER_ID

class Lead(models.Model):
    _inherit = 'crm.lead'

    def website_form_input_filter(self, request, values):
        values.setdefault('medium_id', request.registry['ir.model.data'].xmlid_to_res_id(request.cr, SUPERUSER_ID, 'utm.utm_medium_website'))
        return values
