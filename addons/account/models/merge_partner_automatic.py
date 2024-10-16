from odoo import models
from .mail_message import bypass_token
from odoo.addons import mail


class BasePartnerMergeAutomaticWizard(mail.BasePartnerMergeAutomaticWizard):

    def _update_reference_fields(self, src_partners, dst_partner):
        return super(BasePartnerMergeAutomaticWizard, self.with_context(bypass_audit=bypass_token))._update_reference_fields(src_partners, dst_partner)
