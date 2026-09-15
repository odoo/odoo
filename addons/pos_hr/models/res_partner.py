# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.fields import Domain


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _load_pos_data_domain(self, data, config):
        # Make sure the work contacts of the pos employees are always loaded,
        # they are used as partner on cash in/out statement lines.
        domain = super()._load_pos_data_domain(data, config)
        if config.module_pos_hr:
            employees = self.env['hr.employee'].search(config._employee_domain(config.current_user_id.id))
            work_contact_ids = employees.work_contact_id.ids
            if work_contact_ids:
                domain = Domain.OR([domain, [('id', 'in', work_contact_ids)]])
        return domain
