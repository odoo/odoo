from odoo import api, models, fields


class Users(models.Model):
    _inherit = 'res.users'

    equipment_ids = fields.One2many('maintenance.equipment', 'owner_user_id', string="Managed Equipments")
    equipment_count = fields.Integer(related='employee_id.equipment_count', string="Assigned Equipments")

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

    equipment_ids = fields.One2many('maintenance.equipment', 'employee_id')
    equipment_count = fields.Integer('Equipments', compute='_compute_equipment_count')

    @api.depends('equipment_ids')
    def _compute_equipment_count(self):
        for employee in self:
            employee.equipment_count = len(employee.equipment_ids)
