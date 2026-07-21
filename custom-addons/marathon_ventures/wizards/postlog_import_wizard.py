# -*- coding: utf-8 -*-
"""Postlog import wizard."""

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..services.postlog_import.engine import PostlogImportEngine


class MvPostlogImportWizard(models.TransientModel):
    _name = "mv.postlog.import.wizard"
    _description = "Postlog Import Wizard"

    upload_file = fields.Binary(string="Upload", required=True)
    upload_filename = fields.Char(string="Filename")
    program_id = fields.Many2one("mv.programs", string="Program Record", required=True)
    program_choice = fields.Selection(
        selection="_get_program_selection",
        string="Program",
        required=True,
    )
    import_week = fields.Date(string="Import Week", readonly=True)

    @api.model
    def _get_program_selection(self):
        programs = self.env["mv.programs"].search([], order="name")
        return [(str(program.id), program.display_name) for program in programs]

    @api.onchange("program_choice")
    def _onchange_program_choice(self):
        for wizard in self:
            wizard.program_id = int(wizard.program_choice) if wizard.program_choice else False

    @api.onchange("program_id")
    def _onchange_program_id(self):
        for wizard in self:
            wizard.program_choice = str(wizard.program_id.id) if wizard.program_id else False

    @api.onchange("program_choice", "upload_file", "upload_filename")
    def _onchange_import_defaults(self):
        for wizard in self:
            wizard.import_week = False
            wizard.program_id = int(wizard.program_choice) if wizard.program_choice else False
            if not wizard.program_id or not wizard.upload_file:
                continue

            try:
                _, detected_week = wizard._build_import_engine().extract_rows_and_week()
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

    def action_import(self):
        self.ensure_one()
        if self.program_choice and not self.program_id:
            self.program_id = int(self.program_choice)
        if not self.program_id:
            raise UserError(_("Program is required."))

        engine = self._build_import_engine()
        rows, import_week = engine.extract_rows_and_week()
        self.import_week = import_week
        summary = engine.import_rows(rows, import_week)

        message = _(
            "Imported %(spots)s Spot Data rows for %(program)s, week %(week)s. "
            "Matched: %(matched)s. Unmatched: %(unmatched)s."
        ) % {
            "program": self.program_id.display_name,
            "week": import_week,
            "spots": summary["spot_created"],
            "matched": summary["matched"],
            "unmatched": summary["unmatched"],
        }
        if summary["errors"]:
            message += _("\n\nFirst issues:\n%s") % "\n".join(summary["errors"][:5])

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Postlog Import"),
                "message": message,
                "sticky": bool(summary["errors"]),
                "type": "success" if not summary["errors"] else "warning",
            },
        }
