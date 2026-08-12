# -*- coding: utf-8 -*-
"""Postlog import wizard.

The dropdown now offers the six BUNDLE codes (tegna, hearst,
univision, american_spirit, gray, paid_programming) that the
Node-side handler used - not the list of mv.programs records.
`action_import` creates a `mv.post_log_import` job (see
models/phase28_post_log_import.py) and hands the file off to the
background cron. The user gets a notification saying results will
be emailed.

The old mv.programs-based engine path is kept for backward
compatibility with anything upstream that still creates the wizard
with a `program_id`, but the primary flow is the bundle-code path.
"""
import base64

from odoo import api, fields, models, _
from odoo.exceptions import UserError


_BUNDLE_SELECTION = [
    ('tegna',            'Tegna Connect'),
    ('hearst',           'Hearst Unwired / Primary Hearst Connect'),
    ('univision',        'Univision / Unimas Connect'),
    ('american_spirit',  'American Spirit Connect'),
    ('gray',             'Gray (Bounce / Primary / Retro / Telemundo)'),
    ('paid_programming', 'Paid Programming'),
]


class MvPostlogImportWizard(models.TransientModel):
    _name = "mv.postlog.import.wizard"
    _description = "Postlog Import Wizard"

    upload_file = fields.Binary(string="Upload", required=True)
    upload_filename = fields.Char(string="Filename")
    # Kept as optional legacy plumbing - the primary flow uses the
    # bundle-code path below.
    program_id = fields.Many2one(
        "mv.programs", string="Program Record",
    )
    program_choice = fields.Selection(
        selection=_BUNDLE_SELECTION,
        string="Program",
        required=True,
        help="Bundle program the post-log belongs to. Determines the "
             "column mapping and schedule-matching rules.",
    )
    import_week = fields.Date(string="Import Week", readonly=True)

    # -----------------------------------------------------------------
    # No engine lookup / week autodetect - the phase28 processor does
    # week detection itself from the first row of the file, so we
    # don't need to peek at the upload here.
    # -----------------------------------------------------------------
    def action_import(self):
        """Create a mv.post_log_import job and hand off to the cron."""
        self.ensure_one()
        if not self.program_choice:
            raise UserError(_("Please choose a Program."))
        if not self.upload_file:
            raise UserError(_("Please upload a file."))

        # The phase28 model expects binary data + filename. The wizard
        # already holds those. Copying so the job record owns its own
        # copy of the bytes.
        raw = base64.b64decode(self.upload_file)
        job = self.env['mv.post_log_import'].create({
            'program': self.program_choice,
            'upload_file': base64.b64encode(raw),
            'upload_filename': self.upload_filename or 'postlog.csv',
            'email': self.env.user.email or '',
        })
        # Queue it and trigger the cron. Reuse the action so we keep
        # a single code path for validation + trigger.
        job.action_queue_import()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Postlog Import'),
                'message': _(
                    "Import queued for %(prog)s. You will receive an "
                    "email at %(mail)s with the results when the "
                    "background job finishes."
                ) % {
                    'prog': dict(_BUNDLE_SELECTION).get(
                        self.program_choice, self.program_choice,
                    ),
                    'mail': self.env.user.email or _('your account'),
                },
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
