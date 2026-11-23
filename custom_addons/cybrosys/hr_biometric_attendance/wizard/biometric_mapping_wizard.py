# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class BiometricMappingWizard(models.TransientModel):
    _name = 'biometric.mapping.wizard'
    _description = 'Biometric ID Mapping Wizard'

    device_id = fields.Many2one(
        'biometric.device.details', string='Biometric Device', required=True)
    unmapped_line_ids = fields.One2many(
        'biometric.mapping.wizard.line', 'wizard_id',
        string='Unmapped Biometric IDs')

    @api.model
    def default_get(self, fields_list):
        """Pre-fill the wizard with unmapped biometric IDs"""
        res = super().default_get(fields_list)
        device_id = self.env.context.get('default_device_id')
        if not device_id:
            return res
        device = self.env['biometric.device.details'].browse(device_id)
        # Get all employees with biometric IDs already assigned
        employees_with_bio = self.env['hr.employee'].search([
            ('biometric_user_id', '!=', False),
        ])
        mapped_bio_ids = set()
        for emp in employees_with_bio:
            mapped_bio_ids.add(str(emp.biometric_user_id))
        # Get all biometric IDs from the device
        all_biometric_ids = device.get_all_biometric_ids()
        if not all_biometric_ids:
            return res
        unmapped_vals = []
        for bio_id in all_biometric_ids:
            if bio_id not in mapped_bio_ids:
                unmapped_vals.append((0, 0, {
                    'biometric_id': bio_id,
                    'employee_id': False,
                }))
        res['unmapped_line_ids'] = unmapped_vals
        return res

    def action_apply_mapping(self):
        """Apply the mapping of biometric IDs to employees"""
        self.ensure_one()
        updated_count = 0
        for line in self.unmapped_line_ids:
            if line.employee_id and line.biometric_id:
                # Clear old mapping if this biometric ID was on another employee
                existing = self.env['hr.employee'].search([
                    ('biometric_user_id', '=', int(line.biometric_id)),
                    ('id', '!=', line.employee_id.id),
                ], limit=1)
                if existing:
                    existing.biometric_user_id = False
                # Set the new mapping
                line.employee_id.biometric_user_id = int(line.biometric_id)
                updated_count += 1
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('%d biometric ID(s) mapped to employees.')
                           % updated_count,
                'type': 'success',
                'sticky': False,
            },
        }


class BiometricMappingWizardLine(models.TransientModel):
    _name = 'biometric.mapping.wizard.line'
    _description = 'Biometric ID Mapping Wizard Line'

    wizard_id = fields.Many2one(
        'biometric.mapping.wizard', string='Wizard')
    biometric_id = fields.Char(
        string='Biometric ID', required=True)
    employee_id = fields.Many2one(
        'hr.employee', string='Employee')
    department_id = fields.Many2one(
        related='employee_id.department_id',
        string='Department', readonly=True)
    job_id = fields.Many2one(
        related='employee_id.job_id',
        string='Job Position', readonly=True)

