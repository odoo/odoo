# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.addons.website.models.website import slug
from openerp.exceptions import UserError


class TwitterAgent(models.Model):
    _name = 'twitter.agent'
    _inherit = ['website.published.mixin']

    name = fields.Char(required=True, translate=True)
    description = fields.Text(translate=True)
    user_id = fields.Many2one('res.users', default=lambda self: self.env.uid)
    total_views = fields.Integer()
    state = fields.Selection([('normal', 'Normal'), ('archive', 'Archive')], default='normal')
    tweetus_ids = fields.Many2many('twitter.hashtag', string='Tweet Us Hashtag')
    image = fields.Binary(required=True)
    twitter_access_token = fields.Char()
    twitter_access_token_secret = fields.Char()
    auth_user = fields.Char('Authenticated User Id')
    stream_id = fields.Many2one('twitter.stream', default=lambda self: self.env.ref('website_twitter_wall.twitter_stream_1').id)
    tweet_ids = fields.One2many('twitter.tweet', 'agent_id')

    @api.multi
    @api.depends('name')
    def _website_url(self, name, arg):
        res = super(TwitterAgent, self)._website_url(name, arg)
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        res.update({(wall.id, '%s/twitter_wall/view/%s' % (base_url, slug(wall))) for wall in self})
        return res

    @api.multi
    def write(self, vals):
        """ Restart streaming when state is change from archive to normal """
        res = super(TwitterAgent, self).write(vals)
        if vals.get('state') == 'archive' and not self.auth_user:
            raise UserError(_("You can't archive wall without verify with twitter account"))
        if vals.get('state') == 'normal' and self.auth_user:
            self.stream_id.restart()
        return res

    @api.multi
    def unlink(self):
        """ Override unlink method to restart streaming when deletion perform """
        stream = None
        for wall in self:
            if wall.auth_user:
                stream = wall.stream_id
        super(TwitterAgent, self).unlink()
        if stream:
            stream.restart()


class TwitterHashtag(models.Model):
    _name = 'twitter.hashtag'

    name = fields.Char(required=True)

    _sql_constraints = [('website_twitter_wall_hashtag_unique', 'UNIQUE(name)', 'A hashtag must be unique!')]
