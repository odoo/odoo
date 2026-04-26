# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import urlparse

from odoo import fields, models


class WebsiteDraftField(models.Model):
    _name = 'website.draft.field'
    _description = 'Website Draft Embedded Fields'

    res_model = fields.Char(string='Model', required=True, index=True)
    res_id = fields.Integer(string='Record ID', required=True, index=True)
    website_id = fields.Many2one('website', string='Website', required=True, ondelete='cascade', index=True)
    page_url = fields.Char(string='Page URL', index=True,
                           help='Path of the page on which this draft was last edited.')
    values = fields.Json(string='Draft Values', default=dict)

    _unique_record = models.Constraint(
        'unique(website_id, res_model, res_id)',
        'There can only be one draft per record per website.',
    )

    @staticmethod
    def _page_url_from_request(req):
        """Extract the plain path from the HTTP Referer header so we know
        which page the edit came from."""
        if not req:
            return False
        referrer = req.httprequest.referrer
        if not referrer:
            return False
        return urlparse(referrer).path or False

    def _get_or_create(self, website_id, res_model, res_id, page_url=False):
        """Return the draft record for the given website/model/res_id, creating
        it if it does not exist yet.  Always updates ``page_url`` to the most
        recently edited page."""
        draft = self.search([
            ('website_id', '=', website_id),
            ('res_model', '=', res_model),
            ('res_id', '=', res_id),
        ], limit=1)
        if not draft:
            draft = self.create({
                'website_id': website_id,
                'res_model': res_model,
                'res_id': res_id,
                'page_url': page_url,
            })
        elif page_url and draft.page_url != page_url:
            draft.page_url = page_url
        return draft

    def publish(self):
        """Apply all draft values to the real fields on each record, then delete draft."""
        for draft in self:
            if not draft.values or not draft.res_model:
                continue
            Model = self.env[str(draft.res_model)]
            record = Model.browse(draft.res_id)
            record.write(draft.values)
        self.unlink()
