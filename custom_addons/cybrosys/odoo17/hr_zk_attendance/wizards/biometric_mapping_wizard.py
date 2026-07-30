# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BiometricMappingWizard(models.TransientModel):
    _name = 'biometric.mapping.wizard'
    _description = 'Biometric ID Mapping Wizard'

    device_id = fields.Many2one('biometric.device.details', string='Biometric Device', required=True)
    unmapped_line_ids = fields.One2many('biometric.mapping.wizard.line', 'wizard_id', string='Unmapped Biometric IDs')
    mapped_line_ids = fields.One2many('biometric.mapping.wizard.line', 'wizard_id', string='Mapped Biometric IDs',
                                     domain=[('employee_id', '!=', False)])
    show_mapped = fields.Boolean(string='Show Already Mapped IDs', default=False)

    @api.model
    def default_get(self, fields_list):
        """Pre-fill the wizard with unmapped biometric IDs"""
        res = super(BiometricMappingWizard, self).default_get(fields_list)

        # Get biometric IDs from context
        if self.env.context.get('default_device_id'):
            device_id = self.env.context.get('default_device_id')
            device = self.env['biometric.device.details'].browse(device_id)

            # Get all employees with biometric IDs already assigned
            employees_with_bio = self.env['hr.employee'].search([
                ('biometric_user_id', '!=', False)
            ])

            # Create a dictionary of employee IDs by biometric ID
            mapped_bio_ids = {e.biometric_user_id: e.id for e in employees_with_bio}

            # Get all biometric IDs from the device
            all_biometric_ids = device.get_all_biometric_ids()
            if not all_biometric_ids:
                return res

            # Create separate lists for mapped and unmapped IDs
            unmapped_vals = []
            mapped_vals = []

            for bio_id in all_biometric_ids:
                if bio_id in mapped_bio_ids:
                    # This ID is already mapped to an employee
                    employee = self.env['hr.employee'].browse(mapped_bio_ids[bio_id])
                    mapped_vals.append((0, 0, {
                        'biometric_id': bio_id,
                        'employee_id': employee.id,
                        'original_employee_id': employee.id,
                        'is_already_mapped': True
                    }))
                else:
                    # This ID is not mapped yet
                    unmapped_vals.append((0, 0, {
                        'biometric_id': bio_id,
                        'employee_id': False,
                        'original_employee_id': False,
                        'is_already_mapped': False
                    }))

            res.update({
                'unmapped_line_ids': unmapped_vals,
                'mapped_line_ids': mapped_vals
            })

        return res

    def action_apply_mapping(self):
        """Apply the mapping of biometric IDs to employees"""
        self.ensure_one()

        # Track how many mappings were updated
        updated_count = 0
        already_mapped_count = 0

        # Process unmapped lines first (these are the ones we're primarily changing)
        for line in self.unmapped_line_ids:
            if line.employee_id and line.biometric_id:
                # Check if this biometric ID is used by another employee
                existing = self.env['hr.employee'].search([
                    ('biometric_user_id', '=', line.biometric_id),
                    ('id', '!=', line.employee_id.id)
                ], limit=1)

                if existing:
                    # Clear the old mapping
                    existing.biometric_user_id = False

                # Set the new mapping
                line.employee_id.biometric_user_id = line.biometric_id
                updated_count += 1

        # Process mapped lines - these might have changed mappings
        for line in self.mapped_line_ids:
            if line.is_already_mapped and not line.employee_changed:
                # This was already mapped and hasn't changed
                already_mapped_count += 1
                continue

            if line.employee_id and line.biometric_id:
                # Check if this biometric ID is used by another employee
                existing = self.env['hr.employee'].search([
                    ('biometric_user_id', '=', line.biometric_id),
                    ('id', '!=', line.employee_id.id)
                ], limit=1)

                if existing:
                    # Clear the old mapping
                    existing.biometric_user_id = False

                # Set the new mapping
                line.employee_id.biometric_user_id = line.biometric_id
                updated_count += 1
            elif not line.employee_id and line.is_already_mapped:
                # This mapping was removed
                old_employee = self.env['hr.employee'].search([
                    ('biometric_user_id', '=', line.biometric_id)
                ], limit=1)
                if old_employee:
                    old_employee.biometric_user_id = False
                    updated_count += 1

        message = _('Biometric ID mapping has been updated: %s new mappings, %s unchanged mappings.') % (
            updated_count, already_mapped_count)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': 'success',
                'sticky': False
            }
        }


class BiometricMappingWizardLine(models.TransientModel):
    _name = 'biometric.mapping.wizard.line'
    _description = 'Biometric ID Mapping Wizard Line'

    wizard_id = fields.Many2one('biometric.mapping.wizard', string='Wizard')
    biometric_id = fields.Char(string='Biometric ID', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee')
    department_id = fields.Many2one(related='employee_id.department_id', string='Department', readonly=True)
    job_id = fields.Many2one(related='employee_id.job_id', string='Job Position', readonly=True)
    is_already_mapped = fields.Boolean(string='Already Mapped', default=False)
    original_employee_id = fields.Many2one('hr.employee', string='Original Employee')
    employee_changed = fields.Boolean(string='Mapping Changed', compute='_compute_employee_changed')

    @api.depends('employee_id', 'original_employee_id')
    def _compute_employee_changed(self):
        """Check if the employee mapping has changed"""
        for line in self:
            line.employee_changed = line.is_already_mapped and line.employee_id.id != line.original_employee_id.id
