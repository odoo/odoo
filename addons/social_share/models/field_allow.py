# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class SocialShareModelAllow(models.Model):
    _name = 'social.share.model.allow'
    _description = 'Model allowed as target of share campaigns'

    model_id = fields.Many2one('ir.model', ondelete='cascade', required=True)

class SocialShareFieldAllow(models.Model):
    _name = 'social.share.field.allow'
    _description = 'Field allowed in social share templates'

    model_id = fields.Many2one(related='field_id.model_id', store=True)
    field_id = fields.Many2one('ir.model.fields', ondelete='cascade', required=True)

    # TODO check access rules of all elements when unlinked
