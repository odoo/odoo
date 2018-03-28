# coding: utf-8
from odoo import api, fields, models


class WebsiteURL(models.TransientModel):
    _name = 'website.url'

    url = fields.Char(readonly=True)
    website_id = fields.Many2one('website', required=True, readonly=True)
    wizard_id = fields.Many2one('website.urls.wizard', ondelete='cascade', required=True, readonly=True)
    display_goto = fields.Boolean(required=True, readonly=True)
    published = fields.Boolean('Published')

    @api.multi
    def action_goto(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.url,
            'target': 'self',
        }


class WebsitePublishedWizard(models.TransientModel):
    _name = 'website.urls.wizard'

    path = fields.Char(readonly=True)
    record_id = fields.Integer(required=True, readonly=True)
    model_name = fields.Char(required=True, readonly=True)
    website_urls = fields.One2many('website.url', 'wizard_id')

    @api.model
    def create(self, vals):
        res = super(WebsitePublishedWizard, self).create(vals)

        for website in self.env['website'].search([]):
            self.env['website.url'].create({
                'wizard_id': res.id,
                'url': 'http://%s%s' % (website.domain, res.path if res.path != '#' else ''),
                'display_goto': res.path != '#',
                'website_id': website.id,
                'published': res._get_record().with_context(website_id=website.id).website_published,
            })

        return res

    @api.multi
    def _get_record(self):
        self.ensure_one()
        return self.env[self.model_name].browse(self.record_id)
                                        
    @api.multi
    def action_save(self):
        self.ensure_one()

        for url in self.website_urls:
            self._get_record().with_context(website_id=url.website_id.id).website_published = url.published

        return True
