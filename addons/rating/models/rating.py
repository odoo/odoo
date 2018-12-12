# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import uuid

from odoo import api, fields, models

from odoo.modules.module import get_resource_path

RATING_LIMIT_SATISFIED = 7
RATING_LIMIT_OK = 3
RATING_LIMIT_MIN = 1


class Rating(models.Model):

    _name = "rating.rating"
    _description = "Rating"
    _order = 'write_date desc'
    _rec_name = 'res_name'
    _sql_constraints = [
        ('rating_range', 'check(rating >= 0 and rating <= 10)', 'Rating should be between 0 to 10'),
    ]

    @api.depends('res_model', 'res_id')
    def _compute_res_name(self):
        for rating in self:
            name = self.env[rating.res_model].sudo().browse(rating.res_id).name_get()
            rating.res_name = name and name[0][1] or ('%s/%s') % (rating.res_model, rating.res_id)

    @api.model
    def _default_access_token(self):
        return uuid.uuid4().hex

    res_name = fields.Char(string='Resource name', compute='_compute_res_name', store=True, help="The name of the rated resource.")
    res_model_id = fields.Many2one('ir.model', 'Related Document Model', index=True, ondelete='cascade', help='Model of the followed resource')
    res_model = fields.Char(string='Document Model', related='res_model_id.model', store=True, index=True, readonly=True)
    res_id = fields.Integer(string='Document', required=True, help="Identifier of the rated object", index=True)
    parent_res_name = fields.Char('Parent Document Name', compute='_compute_parent_res_name', store=True)
    parent_res_model_id = fields.Many2one('ir.model', 'Parent Related Document Model', index=True, ondelete='cascade')
    parent_res_model = fields.Char('Parent Document Model', store=True, related='parent_res_model_id.model', index=True, readonly=False)
    parent_res_id = fields.Integer('Parent Document', index=True)
    rated_partner_id = fields.Many2one('res.partner', string="Rated person", help="Owner of the rated resource")
    partner_id = fields.Many2one('res.partner', string='Customer', help="Author of the rating")
    rating = fields.Float(string="Rating Number", group_operator="avg", default=0, help="Rating value: 0=Unhappy, 10=Happy")
    rating_image = fields.Binary('Image', compute='_compute_rating_image')
    rating_text = fields.Selection([
        ('satisfied', 'Satisfied'),
        ('not_satisfied', 'Not satisfied'),
        ('highly_dissatisfied', 'Highly dissatisfied'),
        ('no_rating', 'No Rating yet')], string='Rating', store=True, compute='_compute_rating_text', readonly=True)
    feedback = fields.Text('Comment', help="Reason of the rating")
    message_id = fields.Many2one('mail.message', string="Linked message", help="Associated message when posting a review. Mainly used in website addons.", index=True)
    access_token = fields.Char('Security Token', default=_default_access_token, help="Access token to set the rating of the value")
    consumed = fields.Boolean(string="Filled Rating", help="Enabled if the rating has been filled.")

    @api.depends('parent_res_model', 'parent_res_id')
    def _compute_parent_res_name(self):
        for rating in self:
            name = False
            if rating.parent_res_model and rating.parent_res_id:
                name = self.env[rating.parent_res_model].sudo().browse(rating.parent_res_id).name_get()
                name = name and name[0][1] or ('%s/%s') % (rating.parent_res_model, rating.parent_res_id)
            rating.parent_res_name = name

    @api.multi
    @api.depends('rating')
    def _compute_rating_image(self):
        for rating in self:
            try:
                image_path = get_resource_path('rating', 'static/src/img', 'rating_%s.png' % (int(rating.rating),))
                rating.rating_image = base64.b64encode(open(image_path, 'rb').read())
            except (IOError, OSError):
                rating.rating_image = False

    @api.depends('rating')
    def _compute_rating_text(self):
        for rating in self:
            if rating.rating >= RATING_LIMIT_SATISFIED:
                rating.rating_text = 'satisfied'
            elif rating.rating > RATING_LIMIT_OK:
                rating.rating_text = 'not_satisfied'
            elif rating.rating >= RATING_LIMIT_MIN:
                rating.rating_text = 'highly_dissatisfied'
            else:
                rating.rating_text = 'no_rating'

    @api.model
    def create(self, values):
        if values.get('res_model_id') and values.get('res_id'):
            values.update(self._find_parent_data(values))
        return super(Rating, self).create(values)

    @api.multi
    def write(self, values):
        if values.get('res_model_id') and values.get('res_id'):
            values.update(self._find_parent_data(values))
        return super(Rating, self).write(values)

    def _find_parent_data(self, values):
        """ Determine the parent res_model/res_id, based on the values to create or write """
        current_model_name = self.env['ir.model'].sudo().browse(values['res_model_id']).model
        current_record = self.env[current_model_name].browse(values['res_id'])
        data = {
            'parent_res_model_id': False,
            'parent_res_id': False,
        }
        if hasattr(current_record, '_rating_get_parent_field_name'):
            current_record_parent = current_record._rating_get_parent_field_name()
            if current_record_parent:
                parent_res_model = getattr(current_record, current_record_parent)
                data['parent_res_model_id'] = self.env['ir.model']._get(parent_res_model._name).id
                data['parent_res_id'] = parent_res_model.id
        return data

    @api.multi
    def reset(self):
        for record in self:
            record.write({
                'rating': 0,
                'access_token': record._default_access_token(),
                'feedback': False,
                'consumed': False,
            })

    def action_open_rated_object(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'views': [[False, 'form']]
        }
