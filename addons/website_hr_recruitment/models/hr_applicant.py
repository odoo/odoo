from odoo import _, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    def website_form_input_filter(self, request, values):
        if values.get("job_id"):
            job = self.env["hr.job"].browse(values.get("job_id"))
            if not job.sudo().active:
                _debug.logic("application_refused", reason="job_closed", job=job.id)
                raise UserError(_("The job offer has been closed."))
        return values
