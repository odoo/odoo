from openerp.http import request
from openerp import api, fields, models, SUPERUSER_ID
import md5


class Lead(models.Model):
    _inherit = 'crm.lead'

    @api.one
    def _count_pageviews(self):
        self.pageviews_count = len(self.score_pageview_ids)

    @api.depends('score_ids.value')
    def _compute_score(self):
        self._cr.execute("""
             SELECT
                lead_id, COALESCE(sum(s.value), 0) as sum
             FROM
                crm_lead_score_rel rel
             LEFT JOIN
                website_crm_score s ON (s.id = rel.score_id)
             WHERE lead_id = any(%s)
             GROUP BY lead_id
             """, (self.ids,))
        scores = dict(self._cr.fetchall())
        for lead in self:
            lead.score = scores.get(lead.id, 0)

    score = fields.Float(compute='_compute_score', store=True)
    score_ids = fields.Many2many('website.crm.score', 'crm_lead_score_rel', 'lead_id', 'score_id', string='Score')
    score_pageview_ids = fields.One2many('website.crm.pageview', 'lead_id', string='Page Views', help="List of (tracked) pages seen by the owner of this lead")
    assign_date = fields.Datetime(string='Assign Date', help="Date when the lead has been assigned via the auto-assignation mechanism")
    pageviews_count = fields.Integer('# Page Views', compute='_count_pageviews')
    lang_id = fields.Many2one('res.lang', string='Language', help="Language from the website when lead has been created")

    def encode(self, lead_id):
        encrypted_lead_id = md5.new("%s%s" % (lead_id, self.get_key())).hexdigest()
        return "%s-%s" % (str(lead_id), encrypted_lead_id)

    def decode(self, request):
        # opens the cookie, verifies the signature of the lead_id
        # returns lead_id if the verification passes and None otherwise
        cookie_content = request.httprequest.cookies.get('lead_id')
        if cookie_content:
            lead_id, encrypted_lead_id = cookie_content.split('-', 1)
            expected_encryped_lead_id = md5.new("%s%s" % (lead_id, self.get_key())).hexdigest()
            if encrypted_lead_id == expected_encryped_lead_id:
                return int(lead_id)
            else:
                return None

    def get_key(self):
        return self.pool['ir.config_parameter'].get_param(request.cr, SUPERUSER_ID, 'database.uuid')

    def get_score_domain_cookies(self):
        # TODO should be return request.httprequest.host in master
        return "." + ".".join(request.httprequest.host.rsplit(".", 2)[1:])
