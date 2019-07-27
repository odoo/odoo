# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, tools, fields, models, exceptions, http
from odoo.tools.translate import html_translate


class KarmaError(exceptions.except_orm):
    """ Karma-related error, used for forum and posts. """
    def __init__(self, msg):
        super(KarmaError, self).__init__(msg)


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def serialize_exception(self, e):
        res = super(Http, self).serialize_exception(e)
        if isinstance(e, KarmaError):
            res["exception_type"] = "karma_error"
        return res


class KarmaRank(models.Model):
    _name = 'gamification.karma.rank'
    _description = 'Rank based on karma'
    _order = 'karma_min'

    name = fields.Text(string='Rank Name', translate=True, required=True)
    description = fields.Html(string='Description', translate=html_translate, sanitize_attributes=False,)
    description_motivational = fields.Html(
        string='Motivational', translate=html_translate, sanitize_attributes=False,
        help="Motivational phrase to reach this rank")
    karma_min = fields.Integer(string='Required Karma', help='Minimum karma needed to reach this rank')
    user_ids = fields.One2many('res.users', 'rank_id', string='Users', help="Users having this rank")
    image = fields.Binary('Rank Icon')
    image_medium = fields.Binary(
        "Medium-sized rank icon",
        help="Medium-sized icon of the rank. It is automatically "
             "resized as a 128x128px image, with aspect ratio preserved. "
             "Use this field in form views or some kanban views.")
    image_small = fields.Binary(
        "Small-sized rank icon",
        help="Small-sized icon of the rank. It is automatically "
             "resized as a 64x64px image, with aspect ratio preserved. "
             "Use this field anywhere a small image is required.")

    @api.model_create_multi
    def create(self, values_list):
        for vals in values_list:
            tools.image_resize_images(vals)
        res = super(KarmaRank, self).create(values_list)
        users = self.env['res.users'].sudo().search([('karma', '>', 0)])
        users._recompute_rank()
        return res

    def write(self, vals):
        tools.image_resize_images(vals)
        res = super(KarmaRank, self).write(vals)
        users = self.env['res.users'].sudo().search([('karma', '>', 0)])
        users._recompute_rank()
        return res
