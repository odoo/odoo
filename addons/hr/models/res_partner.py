# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError
from odoo.addons.mail.tools.discuss import Store


class ResPartner(models.Model):
    _inherit = 'res.partner'

    employee_ids = fields.One2many(
        'hr.employee', 'work_contact_id', string='Employees', groups="hr.group_hr_user",
        help="Related employees based on their private address")
    employees_count = fields.Integer(compute='_compute_employees_count', groups="hr.group_hr_user")
    employee = fields.Boolean(help="Whether this contact is an Employee.", compute='_compute_employee', store=True, readonly=False)

    def _compute_employees_count(self):
        for partner in self:
            partner.employees_count = len(partner.sudo().employee_ids.filtered(lambda e: e.company_id in self.env.companies))

    def action_open_employees(self):
        self.ensure_one()
        if self.employees_count > 1:
            return {
                'name': _('Related Employees'),
                'type': 'ir.actions.act_window',
                'res_model': 'hr.employee',
                'view_mode': 'kanban',
                'domain': [('id', 'in', self.employee_ids.ids),
                           ('company_id', 'in', self.env.companies.ids)],
            }
        return {
            'name': _('Employee'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'res_id': self.employee_ids.filtered(lambda e: e.company_id in self.env.companies).id,
            'view_mode': 'form',
        }

    def _get_all_addr(self):
        self.ensure_one()
        employee_id = self.env['hr.employee'].search(
            [('id', 'in', self.employee_ids.ids)],
            limit=1,
        )
        if not employee_id:
            return super()._get_all_addr()

        pstl_addr = {
            'contact_type': 'employee',
            'street': employee_id.private_street,
            'zip': employee_id.private_zip,
            'city': employee_id.private_city,
            'country': employee_id.private_country_id.code,
        }
        return [pstl_addr] + super()._get_all_addr()

    @api.depends('employee_ids')
    def _compute_employee(self):
        employee_data = self.env['hr.employee']._read_group(
            domain=[('work_contact_id', 'in', self.ids)],
            groupby=['work_contact_id'],
        )
        employees = {employee for [employee] in employee_data}
        for partner in self:
            partner.employee = partner in employees

    @api.ondelete(at_uninstall=False)
    def _unlink_contact_rel_employee(self):
        partners = self.filtered(lambda partner: partner.employee)
        if len(self) == 1 and len(partners) == 1 and self.id == partners[0].id:
            raise UserError(_('You cannot delete contact that are linked to an employee, please archive them instead.'))
        if partners:
            error_msg = _(
                'You cannot delete contact(s) linked to employee(s).\n'
                'Please archive them instead.\n\n'
                'Affected contact(s): %(names)s', names=", ".join([u.name for u in partners]),
            )
            action_error = partners._action_show()
            raise RedirectWarning(error_msg, action_error, _('Go to contact'))

    def _action_show(self):
        """If self is a singleton, directly access the form view. If it is a recordset, open a list view"""
        view_id = self.env.ref('base.view_partner_form').id
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'context': {'create': False},
        }
        if len(self) > 1:
            action.update({
                'name': _('Contacts'),
                'view_mode': 'list,form',
                'views': [[None, 'list'], [view_id, 'form']],
                'domain': [('id', 'in', self.ids)],
            })
        else:
            action.update({
                'view_mode': 'form',
                'views': [[view_id, 'form']],
                'res_id': self.id,
            })
        return action

    def _get_store_avatar_card_fields(self, target):
        avatar_card_fields = super()._get_store_avatar_card_fields(target)
        if target.is_internal(self.env):
            # sudo: res.partner - internal users can access employee information of partner
            employee_fields = self.sudo().employee_ids._get_store_avatar_card_fields(target)
            avatar_card_fields.append(Store.Many("employee_ids", employee_fields, mode="ADD", sudo=True))
        return avatar_card_fields
