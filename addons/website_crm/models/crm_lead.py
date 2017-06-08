from openerp import models, SUPERUSER_ID

class Lead(models.Model):
    _inherit = 'crm.lead'

    def website_form_input_filter(self, request, values):
        """Set default medium and team."""
        # Allow the request to include a medium_id
        try:
            values.setdefault("medium_id", self.env.ref('utm.utm_medium_website').id)
        except ValueError:
            pass
        # Do not allow the request to include a team_id
        values["team_id"] = self.env["ir.model.data"].xmlid_to_res_id("website.salesteam_website_sales", False)
        return values
