from odoo import models, fields, api


class WebsiteRewrite(models.Model):
    _name = 'website.rewrite'
    _description = "Website rewrite"

    label = fields.Char('Label', help='Reminder / Reason')
    website_id = fields.Many2one('website', help='Let empty to apply for all yours websites', string="Website")
    active = fields.Boolean(default=True)
    url_from = fields.Char('URL from')
    url_to = fields.Char('URL to')
    action = fields.Selection([
        ('rewrite', 'Rewrite'),
        ('not_found', '404'),
        ('redirect_301', 'Moved permanently'),
        ('redirect_302', 'Moved temporarily')
    ], string='Action todo', default="rewrite")

    name = fields.Char(compute='_compute_name')

    @api.one
    def _compute_name(self):
        self.name = self.label or "%s for %s" % (self.action, self.url_from)
