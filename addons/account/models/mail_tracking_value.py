from odoo import api, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MailTrackingValue(models.Model):
    _inherit = "mail.tracking.value"

    @api.ondelete(at_uninstall=True)
    @_debug.perf.timed
    def _except_audit_log(self):
        _debug.lifecycle("_except_audit_log", records=self)
        self.mail_message_id._except_audit_log()

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        self._except_audit_log()
        return super().write(vals)
