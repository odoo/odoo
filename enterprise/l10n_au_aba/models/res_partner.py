from odoo import models, _


class ResPartner(models.Model):
    _inherit = "res.partner"

    def action_show_details(self):
        """ Opens Contact in a form view with a new window
        """
        self.ensure_one()
        return {
            'name': _("Configure Account"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'res.partner',
            'views': [(False, 'form')],
            'target': 'new',
            'res_id': self.id,
        }
