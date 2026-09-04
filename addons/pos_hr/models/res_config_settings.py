# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

_POS_ROLE_FIELDS = (
    'pos_supervised_employee_ids',
    'pos_restrictive_employee_ids',
    'pos_cashier_employee_ids',
    'pos_manager_employee_ids',
)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # pos.config fields
    pos_supervised_employee_ids = fields.Many2many(related='pos_config_id.supervised_employee_ids', readonly=False,
        help='Can process sales, but a higher level must approve before payment is closed.')
    pos_restrictive_employee_ids = fields.Many2many(related='pos_config_id.restrictive_employee_ids', readonly=False,
        help='Can process sales and close payments, but not apply discounts, refunds, or cancel orders.')
    pos_cashier_employee_ids = fields.Many2many(related='pos_config_id.cashier_employee_ids', readonly=False,
        help=' Full register access. Can process sales, discounts, refunds, and close out payments.')
    pos_manager_employee_ids = fields.Many2many(related='pos_config_id.manager_employee_ids', readonly=False,
        help=' Full access, including reporting, cash management, and session close.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            pos_config_id = vals.get('pos_config_id')
            if pos_config_id:
                vals['pos_manager_employee_ids'] = vals.get('pos_manager_employee_ids', []) + [[4, emp_id] for emp_id in self.env['pos.config'].browse(pos_config_id)._get_group_pos_manager().user_ids.employee_id.ids]
        return super().create(vals_list)

    def _pos_apply_exclusive_role(self, role_field):
        """POS role fields are mutually exclusive: employees listed in `role_field`
        are dropped from every other role field. Employees whose user belongs to
        group_pos_manager may only appear in pos_manager_employee_ids."""
        employees = self[role_field]
        if role_field != 'pos_manager_employee_ids':
            employees -= employees.filtered(
                lambda e: e.user_id and e.user_id._has_group('point_of_sale.group_pos_manager')
            )
            if employees != self[role_field]:
                self[role_field] = employees
        for other_field in _POS_ROLE_FIELDS:
            if other_field != role_field:
                self[other_field] -= employees

    @api.onchange('pos_supervised_employee_ids')
    def _onchange_pos_supervised_employee_ids(self):
        self._pos_apply_exclusive_role('pos_supervised_employee_ids')

    @api.onchange('pos_restrictive_employee_ids')
    def _onchange_pos_restrictive_employee_ids(self):
        self._pos_apply_exclusive_role('pos_restrictive_employee_ids')

    @api.onchange('pos_cashier_employee_ids')
    def _onchange_pos_cashier_employee_ids(self):
        self._pos_apply_exclusive_role('pos_cashier_employee_ids')

    @api.onchange('pos_manager_employee_ids')
    def _onchange_pos_manager_employee_ids(self):
        self._pos_apply_exclusive_role('pos_manager_employee_ids')
