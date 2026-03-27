from odoo import _, api, models
from odoo.exceptions import UserError


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_master_mail_template(self):
        master_xmlids = {
            "account.email_template_edi_invoice",
            "account.email_template_edi_credit_note",
        }
        removed_xml_ids = set(self.get_external_id().values())
        if removed_xml_ids.intersection(master_xmlids):
            raise UserError(_("You cannot delete this mail template, it is used in the invoice sending flow."))
