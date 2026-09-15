from math import asin, cos, radians, sin, sqrt

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrWorkLocation(models.Model):
    _inherit = 'hr.work.location'

    latitude = fields.Float(
        related='address_id.partner_latitude', readonly=False, digits=(10, 7),
        string='Latitude',
    )
    longitude = fields.Float(
        related='address_id.partner_longitude', readonly=False, digits=(10, 7),
        string='Longitude',
    )
    presenly_radius_meters = fields.Float(
        default=150.0, string='Geofence Radius (m)',
    )
    presenly_gps_accuracy_limit_meters = fields.Float(
        default=100.0, string='GPS Accuracy Limit (m)',
    )
    presenly_require_selfie_check_in = fields.Boolean(
        default=True, string='Require Check-In Selfie',
    )
    presenly_require_selfie_check_out = fields.Boolean(
        default=True, string='Require Check-Out Selfie',
    )
    presenly_manager_id = fields.Many2one(
        'res.users', string='Location Manager', check_company=True,
    )
    presenly_approver_ids = fields.Many2many(
        'res.users', 'presenly_work_location_approver_rel',
        'work_location_id', 'user_id', string='Location Approvers',
        check_company=True,
    )
    presenly_is_geofence_ready = fields.Boolean(
        compute='_compute_presenly_is_geofence_ready', store=True,
        string='Geofence Ready',
    )
    presenly_approval_override_count = fields.Integer(
        compute='_compute_presenly_approval_override_count', compute_sudo=True,
        string='Ready Overrides',
    )

    def _compute_presenly_approval_override_count(self):
        counts = dict(self.env['presenly.approval.rule']._read_group(
            [
                ('work_location_id', 'in', self.ids),
                ('active', '=', True),
                ('is_complete', '=', True),
            ],
            ['work_location_id'],
            ['__count'],
        )) if self.ids else {}
        for location in self:
            location.presenly_approval_override_count = counts.get(location, 0)

    def action_open_presenly_approval_overrides(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id(
            'presenly.action_presenly_approval_rule'
        )
        action['name'] = f'Approval Overrides — {self.display_name}'
        action['domain'] = [('work_location_id', '=', self.id)]
        action['context'] = {
            'default_company_id': self.company_id.id,
            'default_work_location_id': self.id,
        }
        return action

    _presenly_radius_positive = models.Constraint(
        'CHECK(presenly_radius_meters > 0)',
        'Geofence radius must be positive.',
    )
    _presenly_gps_accuracy_positive = models.Constraint(
        'CHECK(presenly_gps_accuracy_limit_meters > 0)',
        'GPS accuracy limit must be positive.',
    )

    @api.depends(
        'active', 'name', 'company_id', 'address_id', 'latitude', 'longitude',
        'presenly_radius_meters', 'presenly_gps_accuracy_limit_meters',
    )
    def _compute_presenly_is_geofence_ready(self):
        for location in self:
            location.presenly_is_geofence_ready = bool(
                location.active
                and location.name
                and location.company_id
                and location.address_id
                and (location.latitude or location.longitude)
                and -90 <= location.latitude <= 90
                and -180 <= location.longitude <= 180
                and location.presenly_radius_meters > 0
                and location.presenly_gps_accuracy_limit_meters > 0
            )

    @staticmethod
    def _validate_latitude_longitude(latitude, longitude):
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValidationError('Coordinates are outside the valid range.')

    @staticmethod
    def _haversine_distance_meters(latitude_a, longitude_a, latitude_b, longitude_b):
        earth_radius = 6371000
        delta_lat = radians(latitude_b - latitude_a)
        delta_lon = radians(longitude_b - longitude_a)
        value = (
            sin(delta_lat / 2) ** 2
            + cos(radians(latitude_a))
            * cos(radians(latitude_b))
            * sin(delta_lon / 2) ** 2
        )
        return 2 * earth_radius * asin(sqrt(value))

    def is_coordinate_allowed(self, latitude, longitude, accuracy=None):
        self.ensure_one()
        if not self.presenly_is_geofence_ready:
            return False
        self._validate_latitude_longitude(latitude, longitude)
        if (
            accuracy is not None
            and accuracy > self.presenly_gps_accuracy_limit_meters
        ):
            return False
        return self._haversine_distance_meters(
            self.latitude, self.longitude, latitude, longitude,
        ) <= self.presenly_radius_meters

    @api.model
    def _presenly_migrate_native_structure(self):
        """Backfill native references without deleting or changing workflows."""
        for model_name, field_name in (
            ('presenly.permission', 'work_location_id'),
            ('hr.leave', 'presenly_work_location_id'),
        ):
            records = self.env[model_name].sudo().search([
                (field_name, '=', False),
                ('employee_id.work_location_id', '!=', False),
            ])
            for record in records:
                primary = record.employee_id.work_location_id
                if primary.company_id == record.company_id:
                    record.with_context(presenly_workflow=True).write({
                        field_name: primary.id,
                    })

        attendances = self.env['hr.attendance'].sudo().search([
            '|',
            ('presenly_company_id', '=', False),
            ('presenly_work_location_id', '=', False),
        ])
        for attendance in attendances:
            values = {}
            company = attendance.employee_id.company_id
            if not attendance.presenly_company_id and company:
                values['presenly_company_id'] = company.id
            if not attendance.presenly_work_location_id and attendance.presenly_attendance_mode != 'wfa':
                evidence_location = attendance.presenly_event_ids.filtered(
                    lambda event: event.work_location_id
                    and event.work_location_id.company_id == company
                )[:1].work_location_id
                fallback_location = attendance.employee_id.work_location_id
                location = evidence_location or fallback_location
                if location and location.company_id == company:
                    values['presenly_work_location_id'] = location.id
            if values:
                attendance._presenly_migration_write(values)
        return True

