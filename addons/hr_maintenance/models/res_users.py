from odoo import api, models, fields


class Users(models.Model):
    _inherit = 'res.users'

    equipment_ids = fields.One2many('maintenance.equipment', 'owner_user_id')
    equipment_count = fields.Integer('Equipments', compute='_compute_equipment_count')

    @api.depends('equipment_ids')
    def _compute_equipment_count(self):
        for user in self:
            user.equipment_count = len(user.equipment_ids)

    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights.
            Access rights are disabled by default, but allowed
            on some specific fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.
        """
        init_res = super(Users, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        type(self).SELF_READABLE_FIELDS = type(self).SELF_READABLE_FIELDS + ['equipment_count']
        return init_res


class Employee(models.Model):
    _inherit = 'hr.employee'

    equipment_count = fields.Integer(related='user_id.equipment_count')
