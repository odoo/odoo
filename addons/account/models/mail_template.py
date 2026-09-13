from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MailTemplate(models.Model):
    _inherit = "mail.template"

    @api.ondelete(at_uninstall=False)
    @_debug.perf.timed
    def _unlink_except_master_mail_template(self):
        _debug.lifecycle("_unlink_except_master_mail_template", records=self)
        master_xmlids = {
            "account.email_template_edi_invoice",
            "account.email_template_edi_credit_note",
        }
        removed_xml_ids = set(self.get_external_id().values())
        if removed_xml_ids.intersection(master_xmlids):
            raise UserError(
                _(
                    "You cannot delete this mail template, it is used in the invoice sending flow."
                )
            )
