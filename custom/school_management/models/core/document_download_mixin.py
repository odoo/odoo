from markupsafe import Markup

from odoo import _, models
from odoo.exceptions import AccessError, UserError


class DocumentDownloadMixin(models.AbstractModel):
    _name = 'university.document.download.mixin'
    _description = 'University Document Download Mixin'

    _download_report_xmlid = None   # needed for PDF only, e.g. 'school_management.action_report_university_report_card'
    _download_states = ()           # tuple of allowed state strings; empty = any state
    _download_groups = ()           # group xmlids; empty = any user with read access

    def _check_download_allowed(self, need_report=True):
        self.ensure_one()
        if need_report and not self._download_report_xmlid:
            raise UserError(_('No report is configured for this document.'))
        if self._download_groups and not self.env.su:
            if not any(self.env.user.has_group(g) for g in self._download_groups):
                raise AccessError(_('You are not allowed to download this document.'))
        if self._download_states and 'state' in self._fields:
            if self.state not in self._download_states:
                raise UserError(_("This document can't be downloaded in its current state."))

    def _log_download(self, file_type='PDF'):
        """Log an audit note in the record chatter (and linked student profile)."""
        self.ensure_one()
        user_name = self.env.user.name or _('User')
        doc_name = self.display_name or self._description

        body = Markup(
            "<p>📄 <strong>Document Downloaded:</strong> %(doc)s (<em>%(format)s</em>) by %(user)s</p>"
        ) % {
            "doc": doc_name,
            "format": file_type,
            "user": user_name,
        }

        # Post note to current record if it supports chatter
        if hasattr(self, 'message_post'):
            try:
                self.message_post(
                    body=body,
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
            except Exception:
                pass

        # Also post note to student profile if linked and distinct from self
        if hasattr(self, 'student_id') and self.student_id and hasattr(self.student_id, 'message_post') and self.student_id != self:
            try:
                student_body = Markup(
                    "<p>📄 <strong>Academic Document Downloaded:</strong> %(doc)s (<em>%(format)s</em>) by %(user)s</p>"
                ) % {
                    "doc": doc_name,
                    "format": file_type,
                    "user": user_name,
                }
                self.student_id.message_post(
                    body=student_body,
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
            except Exception:
                pass

    # ---------- PDF ----------
    def action_download_document(self):
        self._check_download_allowed(need_report=True)
        self._log_download(file_type='PDF')
        report = self.env.ref(self._download_report_xmlid)
        return report.report_action(self)

    # ---------- Excel ----------
    def _get_xlsx_data(self):
        """Override in each model.
        Return (sheet_name, headers, rows) where rows is a list of lists."""
        self.ensure_one()
        return (
            'Document',
            ['Name', 'State'],
            [[self.display_name, self.state if 'state' in self._fields else '']],
        )

    def action_download_xlsx(self):
        self._check_download_allowed(need_report=False)
        self._log_download(file_type='Excel')
        return {
            'type': 'ir.actions.act_url',
            'url': f'/university/document/{self._name}/{self.id}/download/xlsx',
            'target': 'self',
        }
