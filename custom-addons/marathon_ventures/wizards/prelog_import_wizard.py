# -*- coding: utf-8 -*-
"""Prelog import wizard.

Supports CSV, XLS and XLSX uploads for a selected Program + Prelog Version.
The upload currently replaces an existing Program/week/version wholesale when
the user confirms; appending or partial uploads are intentionally unsupported.
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

from ..services.prelog_import.engine import PrelogImportEngine


class MvPrelogImportWizard(models.TransientModel):
    _name = 'mv.prelog.import.wizard'
    _description = 'Prelog Import Wizard'

    _VERSION_SELECTION = [(str(i), str(i)) for i in range(1, 7)]

    upload_file = fields.Binary(string='Upload', required=True)
    upload_filename = fields.Char(string='Filename')
    program_id = fields.Many2one('mv.programs', string='Program Record', required=True)
    program_choice = fields.Selection(
        selection='_get_program_selection',
        string='Program',
        required=True,
    )
    prelog_version = fields.Selection(
        selection=_VERSION_SELECTION,
        string='Prelog Version',
        required=True,
        default='1',
    )
    import_week = fields.Date(string='Import Week', readonly=True)

    @api.model
    def _get_program_selection(self):
        programs = self.env['mv.programs'].search([], order='name')
        return [(str(program.id), program.display_name) for program in programs]

    @api.onchange('program_choice')
    def _onchange_program_choice(self):
        for wizard in self:
            wizard.program_id = int(wizard.program_choice) if wizard.program_choice else False

    @api.onchange('program_id')
    def _onchange_program_id(self):
        for wizard in self:
            wizard.program_choice = str(wizard.program_id.id) if wizard.program_id else False

    @api.onchange('program_choice', 'upload_file', 'upload_filename')
    def _onchange_import_defaults(self):
        for wizard in self:
            wizard.import_week = False
            wizard.program_id = int(wizard.program_choice) if wizard.program_choice else False
            if not wizard.program_id or not wizard.upload_file:
                if not wizard.prelog_version:
                    wizard.prelog_version = '1'
                continue

            try:
                _, detected_week = wizard._build_import_engine().extract_rows_and_week()
            except UserError:
                continue

            wizard.import_week = detected_week
            wizard.prelog_version = str(wizard._get_next_prelog_version(detected_week))

    def _build_import_engine(self):
        self.ensure_one()
        return PrelogImportEngine(
            self.env,
            program=self.program_id,
            upload_file=self.upload_file,
            upload_filename=self.upload_filename,
        )

    def _get_next_prelog_version(self, import_week):
        self.ensure_one()
        if not self.program_id or not import_week:
            return 1
        existing_versions = self.env['mv.prelog_data'].search([
            '|',
            '&',
            ('import_program', '=', self.program_id.id),
            ('import_week_value', '=', import_week),
            '&',
            ('schedule.deal_parent.program', '=', self.program_id.id),
            ('schedule.week', '=', import_week),
        ]).mapped('version')
        existing_versions = {int(version) for version in existing_versions if version}
        next_version = len(existing_versions) + 1
        if next_version > 6:
            return 1
        return max(next_version, 1)

    @staticmethod
    def _validate_prelog_version(version):
        if version < 1 or version > 6:
            raise ValidationError(_("Prelog Version must be between 1 and 6."))

    def _existing_prelogs(self, import_week, version):
        self.ensure_one()
        return self.env['mv.prelog_data'].search([
            ('version', '=', version),
            '|',
            '&',
            ('import_program', '=', self.program_id.id),
            ('import_week_value', '=', import_week),
            '&',
            ('schedule.deal_parent.program', '=', self.program_id.id),
            ('schedule.week', '=', import_week),
        ])

    def _run_import(self, *, force_replace=False):
        self.ensure_one()
        if self.program_choice and not self.program_id:
            self.program_id = int(self.program_choice)
        if not self.program_id:
            raise UserError(_("Program is required."))
        engine = self._build_import_engine()
        extracted_rows, import_week = engine.extract_rows_and_week()
        self.import_week = import_week
        version = int(self.prelog_version or 0)
        self._validate_prelog_version(version)

        existing_prelogs = self._existing_prelogs(import_week, version)
        if existing_prelogs and not force_replace:
            wizard = self.env['mv.prelog.import.confirm.wizard'].create({
                'import_wizard_id': self.id,
                'version_number': version,
            })
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'mv.prelog.import.confirm.wizard',
                'res_id': wizard.id,
                'view_mode': 'form',
                'target': 'new',
            }

        job, created = self.env['mv.prelog_import_job'].create_from_wizard(
            program=self.program_id,
            upload_file=self.upload_file,
            upload_filename=self.upload_filename,
            import_week=import_week,
            prelog_version=version,
            replace_existing=bool(existing_prelogs),
        )
        self.program_id.prelog_version = version

        if created:
            message = _(
                "Upload started for %(program)s, week %(week)s, version %(version)s. "
                "You'll receive an email when it finishes."
            ) % {
                'program': self.program_id.display_name,
                'week': import_week,
                'version': version,
            }
        else:
            message = _(
                "An identical upload is already %(state)s for %(program)s, week %(week)s, version %(version)s. "
                "You'll receive an email when it finishes."
            ) % {
                'state': job.state,
                'program': self.program_id.display_name,
                'week': import_week,
                'version': version,
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': _('Prelog Import'), 'message': message, 'sticky': False, 'type': 'success'},
        }

    def action_import(self):
        self.ensure_one()
        return self._run_import(force_replace=False)


class MvPrelogImportConfirmWizard(models.TransientModel):
    _name = 'mv.prelog.import.confirm.wizard'
    _description = 'Prelog Import Replace Confirmation'

    import_wizard_id = fields.Many2one('mv.prelog.import.wizard', required=True)
    version_number = fields.Integer(string='Version', required=True)
    confirmation_message = fields.Text(
        string='Message',
        compute='_compute_confirmation_message',
    )

    @api.depends('version_number')
    def _compute_confirmation_message(self):
        for wizard in self:
            wizard.confirmation_message = _("Are you sure you want to delete version %s and re-upload?") % wizard.version_number

    def action_confirm(self):
        self.ensure_one()
        return self.import_wizard_id._run_import(force_replace=True)
