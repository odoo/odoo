# -*- coding: utf-8 -*-
"""Postlog import wizard.

One entry point for every postlog, routed by the Program's own **Program Type**
(``mv.programs.cable_synd``) so the operator never has to know which engine
handles their file:

    Cable        -> config-driven engine, creates mv.postlog_import_job, and the
                    rows land in the Postlog Workbench.
    Bundle       -> phase28 bundle processor (mv.post_log_import). One Program
                    record per bundle, mapped to phase28's code below.
    PP           -> phase28, 'paid_programming'. Self-identifying.
    Digital      -> not built yet; Import is blocked.
    GM           -> not built yet; Import is blocked.
    Syndication  -> not built yet; Import is blocked.
    (not set)    -> blocked, telling the user to set Program Type.

Blocking rather than guessing is deliberate: a Selection has a real blank state,
so "nobody configured this Program" is distinguishable from a real choice.

The prelog side keeps its own wizard (mv.prelog.import.wizard); this one mirrors
its dual program_id/program_choice pattern and its notification shape.
"""
import base64

from odoo import models, fields, api, _
from odoo.exceptions import UserError

from ..services.postlog_import.engine import PostlogImportEngine


# phase28 dispatches on a code string and has no link to mv.programs, so the
# mapping lives here. There is exactly one Program record per bundle.
# A Bundle Program missing from this map is refused rather than guessed, so a
# rename in prod fails loudly instead of importing through the wrong handler.
_BUNDLE_CODE_BY_PROGRAM = {
    'tegna connect': 'tegna',
    'hearst unwired': 'hearst',
    'univision connect': 'univision',
    'american spirit connect': 'american_spirit',
    'gray': 'gray',
}

# Program Types that route to our config-driven engine.
_POSTLOG_TYPES = ('cable',)
# Program Types that route to phase28.
_BUNDLE_TYPES = ('bundle', 'pp')
# Program Types we have not built a postlog path for yet.
_UNSUPPORTED_TYPES = ('digital', 'gm', 'syndication')


class MvPostlogUploadWizard(models.TransientModel):
    _name = 'mv.postlog.upload.wizard'
    _description = 'Postlog Import Wizard'

    upload_file = fields.Binary(string='Upload', required=True)
    upload_filename = fields.Char(string='Filename')
    program_id = fields.Many2one('mv.programs', string='Program Record', required=True)
    program_choice = fields.Selection(
        selection='_get_program_selection',
        string='Program',
        required=True,
    )
    import_week = fields.Date(string='Import Week', readonly=True)

    program_type = fields.Selection(
        related='program_id.cable_synd',
        string='Program Type',
        readonly=True,
    )
    route = fields.Selection(
        [
            ('postlog', 'Postlog Data'),
            ('bundle', 'Bundle'),
            ('unsupported', 'Not Supported'),
            ('unset', 'Program Type Not Set'),
            ('unmapped', 'Bundle Not Mapped'),
        ],
        string='Route',
        compute='_compute_route',
    )
    route_message = fields.Char(string='Routing', compute='_compute_route')
    can_import = fields.Boolean(compute='_compute_route')

    @api.model
    def _get_program_selection(self):
        programs = self.env['mv.programs'].search([], order='name')
        return [(str(program.id), program.display_name) for program in programs]

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    @api.depends('program_id', 'program_id.cable_synd')
    def _compute_route(self):
        type_labels = dict(
            self.env['mv.programs']._fields['cable_synd'].selection
        )
        for wizard in self:
            program = wizard.program_id
            program_type = program.cable_synd if program else False
            label = type_labels.get(program_type, program_type)

            if not program:
                wizard.route = 'unset'
                wizard.route_message = _('Choose a Program.')
                wizard.can_import = False
            elif not program_type:
                wizard.route = 'unset'
                wizard.route_message = _(
                    '%(program)s has no Program Type set. Set it on the Program '
                    'record before importing a postlog.'
                ) % {'program': program.display_name}
                wizard.can_import = False
            elif program_type in _POSTLOG_TYPES:
                wizard.route = 'postlog'
                wizard.route_message = _(
                    '%(type)s - imports as Postlog Data and appears in the '
                    'Postlog Workbench.'
                ) % {'type': label}
                wizard.can_import = True
            elif program_type in _BUNDLE_TYPES:
                code = wizard._bundle_code()
                if not code:
                    wizard.route = 'unmapped'
                    wizard.route_message = _(
                        '%(program)s is a Bundle Program but is not mapped to a '
                        'bundle processor. Ask a developer to add it.'
                    ) % {'program': program.display_name}
                    wizard.can_import = False
                else:
                    wizard.route = 'bundle'
                    wizard.route_message = _(
                        '%(type)s - handed to the bundle processor (%(code)s). '
                        'Results are emailed; these rows do not appear in the '
                        'Postlog Workbench.'
                    ) % {'type': label, 'code': code}
                    wizard.can_import = True
            elif program_type in _UNSUPPORTED_TYPES:
                wizard.route = 'unsupported'
                wizard.route_message = _(
                    '%(type)s postlog import has not been built yet.'
                ) % {'type': label}
                wizard.can_import = False
            else:
                wizard.route = 'unsupported'
                wizard.route_message = _(
                    'Program Type %(type)s has no postlog import path.'
                ) % {'type': label}
                wizard.can_import = False

    def _bundle_code(self):
        """phase28 code for this Program, or False when it is not mapped."""
        self.ensure_one()
        if self.program_id.cable_synd == 'pp':
            return 'paid_programming'
        key = (self.program_id.display_name or '').strip().lower()
        return _BUNDLE_CODE_BY_PROGRAM.get(key, False)

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------

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
            # Only our engine derives a week from the file. A bundle file has a
            # different layout, so parsing it here would just raise.
            if wizard.route != 'postlog' or not wizard.upload_file:
                continue
            try:
                _rows, detected_week = wizard._build_import_engine().extract_rows_and_week()
            except UserError:
                continue
            wizard.import_week = detected_week

    def _build_import_engine(self):
        self.ensure_one()
        return PostlogImportEngine(
            self.env,
            program=self.program_id,
            upload_file=self.upload_file,
            upload_filename=self.upload_filename,
        )

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    def action_import(self):
        self.ensure_one()
        if self.program_choice and not self.program_id:
            self.program_id = int(self.program_choice)
        if not self.program_id:
            raise UserError(_("Program is required."))
        if not self.upload_file:
            raise UserError(_("Upload a file first."))

        # The view hides Import for these, but guard server-side too.
        if not self.can_import:
            raise UserError(self.route_message)

        if self.route == 'bundle':
            return self._run_bundle_import()
        return self._run_postlog_import()

    def _run_postlog_import(self):
        self.ensure_one()
        engine = self._build_import_engine()
        _rows, import_week = engine.extract_rows_and_week()
        self.import_week = import_week

        # Raises if this Program/week already has Postlog Data.
        job, created = self.env['mv.postlog_import_job'].create_from_wizard(
            program=self.program_id,
            upload_file=self.upload_file,
            upload_filename=self.upload_filename,
            import_week=import_week,
        )
        if created:
            message = _(
                "Upload started for %(program)s, week %(week)s. "
                "You'll receive an email when it finishes."
            ) % {'program': self.program_id.display_name, 'week': import_week}
        else:
            message = _(
                "An identical upload is already %(state)s for %(program)s, week %(week)s. "
                "You'll receive an email when it finishes."
            ) % {
                'state': job.state,
                'program': self.program_id.display_name,
                'week': import_week,
            }
        return self._notify(_('Postlog Import'), message)

    def _run_bundle_import(self):
        """Hand the file to the phase28 bundle processor."""
        self.ensure_one()
        code = self._bundle_code()
        if not code:
            raise UserError(self.route_message)

        raw = base64.b64decode(self.upload_file)
        job = self.env['mv.post_log_import'].create({
            'program': code,
            'upload_file': base64.b64encode(raw),
            'upload_filename': self.upload_filename or 'postlog.csv',
            'email': self.env.user.email or '',
        })
        job.action_queue_import()
        return self._notify(
            _('Postlog Import'),
            _(
                "Bundle import queued for %(program)s. You will receive an email "
                "at %(mail)s with the results when the background job finishes."
            ) % {
                'program': self.program_id.display_name,
                'mail': self.env.user.email or _('your account'),
            },
        )

    @staticmethod
    def _notify(title, message):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'sticky': False,
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
