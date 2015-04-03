from openerp import models, fields, api, _
from openerp.addons.website.models.website import slug
from urlparse import urljoin

class HrRecruitmentSource(models.Model):
    _inherit = 'hr.recruitment.source'

    @api.depends('source_id')
    def _compute_url(self):
        result = super(HrRecruitmentSource, self)._get_url(False, False)
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        for source in result.keys():
            job_id = self.browse(source).job_id
            self.url = urljoin(base_url, "/jobs/detail/%s?%s" % (slug(job_id), result[source]))

    url = fields.Char(compute='_compute_url', string='Url Parameters')

