# -*- coding: utf-8 -*-

from urlparse import urlsplit
from openerp import api, fields, models


class HrEquipmentConfigSettings(models.TransientModel):
    _name = 'hr.equipment.config.settings'
    _inherit = 'res.config.settings'

    equipment_alias_prefix = fields.Char('Use the following alias to report internal equipment issue')
    alias_domain = fields.Char("Alias Domain")

    @api.multi
    def get_default_alias_equipment(self):
        alias_name = False
        alias_id = self.env.ref('hr_equipment.mail_alias_equipment')
        if alias_id:
            alias_name = alias_id.alias_name
        return {'equipment_alias_prefix': alias_name}

    @api.multi
    def set_default_alias_equipment(self):
        for record in self:
            default_equipment_alias_prefix = record.get_default_alias_equipment()['equipment_alias_prefix']
            if record.equipment_alias_prefix != default_equipment_alias_prefix:
                alias_id = self.env.ref('hr_equipment.mail_alias_equipment')
                if alias_id:
                    alias_id.write({'alias_name': record.equipment_alias_prefix})
        return True

    @api.multi
    def get_default_alias_domain(self):
        alias_domain = self.env['ir.config_parameter'].get_param("mail.catchall.domain")
        if not alias_domain:
            domain = self.env["ir.config_parameter"].get_param("web.base.url")
            try:
                alias_domain = urlsplit(domain).netloc.split(':')[0]
            except Exception:
                pass
        return {'alias_domain': alias_domain}

