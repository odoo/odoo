from odoo import fields, models, api


class Partner(models.Model):
    _inherit = 'res.partner'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if self._context.get('active_model') == 'hr.applicant':
                vals['type'] = 'private'
        return super(Partner, self).create(vals_list)

