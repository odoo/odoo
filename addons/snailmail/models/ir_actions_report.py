from odoo import models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _get_attachments(self, records, filenames=None):
        # Force a re-render rather than reuse: a snailmail render is a different
        # document from the stored one, because get_paperformat below forces
        # euro/A4 for it.
        #
        # On the batch method, not on a per-record one, because the question is
        # about the render and not about any record -- none of this reads
        # `records`. Asked per record it also cost the caller its batched
        # search: it had to compare method identity to find out whether the
        # singular hook was overridden, and once this module was installed that
        # comparison failed for EVERY report, dropping every render onto one
        # ir.attachment search per record.
        if self.env.context.get("snailmail_layout"):
            return {}
        return super()._get_attachments(records, filenames)

    def get_paperformat(self):
        # force the right format (euro/A4) when sending letters, only if we are not using the l10n_DE layout
        res = super().get_paperformat()
        if self.env.context.get("snailmail_layout") and res != self.env.ref(
            "l10n_de.paperformat_euro_din", False
        ):
            return self.env.ref("base.paperformat_euro")
        else:
            return res
