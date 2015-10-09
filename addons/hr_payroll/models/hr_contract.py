# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrContract(models.Model):
    """
    Employee contract based on the visa, work permits
    allows to configure different Salary structure
    """

    _inherit = 'hr.contract'

    struct_id = fields.Many2one('hr.payroll.structure', 'Salary Structure')
    schedule_pay = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi-annually', 'Semi-annually'),
        ('annually', 'Annually'),
        ('weekly', 'Weekly'),
        ('bi-weekly', 'Bi-weekly'),
        ('bi-monthly', 'Bi-monthly'),
    ], 'Scheduled Pay', index=True, default='monthly')

    def get_all_structures(self):
        """
        :return: the structures linked to the given contracts, ordered by hierachy (parent=False first, then first level children and so on) and without duplicate
        """
        structures = self.mapped('struct_id')
        return self.env['hr.payroll.structure'].browse(structures._get_parent_structure())
