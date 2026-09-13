from urllib.parse import urlencode

from odoo import api, fields, models
from odoo.libs.web import urls


class HrRecruitmentSource(models.Model):
    _inherit = "hr.recruitment.source"

    url = fields.Char(
        string="Tracker URL",
        compute="_compute_url",
    )

    @api.depends("source_id", "source_id.name", "job_id", "job_id.company_id")
    def _compute_url(self):
        for source in self:
            source.url = urls.urljoin(
                source.job_id.get_base_url(),
                "%s?%s"
                % (
                    source.job_id.website_url,
                    urlencode(
                        {
                            "utm_campaign": self.env.ref(
                                "hr_recruitment.utm_campaign_job"
                            ).name,
                            "utm_medium": source.medium_id.name
                            or self.env["utm.medium"]
                            ._get_or_create_utm_medium("website")
                            .name,
                            "utm_source": source.source_id.name or None,
                        }
                    ),
                ),
            )
