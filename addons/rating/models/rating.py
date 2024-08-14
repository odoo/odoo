# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import uuid

from odoo import api, fields, models
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.rating.models import rating_data
from odoo.tools.misc import file_open


class Rating(models.Model):
    _name = "rating.rating"
    _description = "Rating"
    _order = 'write_date desc, id desc'
    _rec_name = 'res_name'

    @api.model
    def _default_access_token(self):
        return uuid.uuid4().hex

    @api.model
    def _selection_target_model(self):
        return [(model.model, model.name) for model in self.env['ir.model'].sudo().search([])]

    create_date = fields.Datetime(string="Submitted on")
    res_name = fields.Char(string='Resource name', compute='_compute_res_name', store=True)
    res_model_id = fields.Many2one('ir.model', 'Related Document Model', index=True, ondelete='cascade')
    res_model = fields.Char(string='Document Model', related='res_model_id.model', store=True, index=True, readonly=True)
    res_id = fields.Many2oneReference(string='Document', model_field='res_model', required=True, index=True)
    resource_ref = fields.Reference(
        string='Resource Ref', selection='_selection_target_model',
        compute='_compute_resource_ref', readonly=True)
    parent_res_name = fields.Char('Parent Document Name', compute='_compute_parent_res_name', store=True)
    parent_res_model_id = fields.Many2one('ir.model', 'Parent Related Document Model', index=True, ondelete='cascade')
    parent_res_model = fields.Char('Parent Document Model', store=True, related='parent_res_model_id.model', index=True, readonly=False)
    parent_res_id = fields.Integer('Parent Document', index=True)
    parent_ref = fields.Reference(
        string='Parent Ref', selection='_selection_target_model',
        compute='_compute_parent_ref', readonly=True)
    rated_partner_id = fields.Many2one('res.partner', string="Rated Operator")
    rated_partner_name = fields.Char(related="rated_partner_id.name")
    partner_id = fields.Many2one('res.partner', string='Customer')
    rating = fields.Float(string="Rating Value", aggregator="avg", default=0)
    rating_image = fields.Binary('Image', compute='_compute_rating_image')
    rating_image_url = fields.Char('Image URL', compute='_compute_rating_image')
    rating_text = fields.Selection(rating_data.RATING_TEXT, string='Rating', store=True, compute='_compute_rating_text', readonly=True)
    feedback = fields.Text('Comment')
    message_id = fields.Many2one(
        'mail.message', string="Message",
        index=True, ondelete='cascade')
    is_internal = fields.Boolean('Visible Internally Only', readonly=False, related='message_id.is_internal', store=True)
    access_token = fields.Char('Security Token', default=_default_access_token)
    consumed = fields.Boolean(string="Filled Rating")

    _sql_constraints = [
        ('rating_range', 'check(rating >= 0 and rating <= 5)', 'Rating should be between 0 and 5'),
    ]

    @api.depends('res_model', 'res_id')
    def _compute_res_name(self):
        for rating in self:
            name = self.env[rating.res_model].sudo().browse(rating.res_id).display_name
            rating.res_name = name or f'{rating.res_model}/{rating.res_id}'

    @api.depends('res_model', 'res_id')
    def _compute_resource_ref(self):
        for rating in self:
            if rating.res_model and rating.res_model in self.env:
                rating.resource_ref = '%s,%s' % (rating.res_model, rating.res_id or 0)
            else:
                rating.resource_ref = None

    @api.depends('parent_res_model', 'parent_res_id')
    def _compute_parent_ref(self):
        for rating in self:
            if rating.parent_res_model and rating.parent_res_model in self.env:
                rating.parent_ref = '%s,%s' % (rating.parent_res_model, rating.parent_res_id or 0)
            else:
                rating.parent_ref = None

    @api.depends('parent_res_model', 'parent_res_id')
    def _compute_parent_res_name(self):
        for rating in self:
            name = False
            if rating.parent_res_model and rating.parent_res_id:
                name = self.env[rating.parent_res_model].sudo().browse(rating.parent_res_id).display_name
                name = name or f'{rating.parent_res_model}/{rating.parent_res_id}'
            rating.parent_res_name = name

    def _get_rating_image_filename(self):
        self.ensure_one()
        return 'rating_%s.png' % rating_data._rating_to_threshold(self.rating)

    @api.depends('rating')
    def _compute_rating_image(self):
        self.rating_image_url = False
        self.rating_image = False
        for rating in self:
            image_path = f'rating/static/src/img/{rating._get_rating_image_filename()}'
            rating.rating_image_url = f'/{image_path}'
            try:
                rating.rating_image = base64.b64encode(
                    file_open(image_path, 'rb', filter_ext=('.png',)).read())
            except (IOError, OSError, FileNotFoundError):
                rating.rating_image = False

    @api.depends('rating')
    def _compute_rating_text(self):
        for rating in self:
            rating.rating_text = rating_data._rating_to_text(rating.rating)

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get('res_model_id') and values.get('res_id'):
                values.update(self._find_parent_data(values))
        return super().create(vals_list)

    def write(self, values):
        if values.get('res_model_id') and values.get('res_id'):
            values.update(self._find_parent_data(values))
        return super(Rating, self).write(values)

    def unlink(self):
        # OPW-2181568: Delete the chatter message too
        self.env['mail.message'].search([('rating_ids', 'in', self.ids)]).unlink()
        return super(Rating, self).unlink()

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

    # ------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------

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

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    def _classify_by_model(self):
        """ To ease batch computation of various ratings related methods they
        are classified by model. Ratings not linked to a valid record through
        res_model / res_id are ignored.

        :return dict: for each model having at least one rating in self, have
          a sub-dict containing
            * ratings: ratings related to that model;
            * record IDs: records linked to the ratings of that model, in same
              order;
        """
        data_by_model = {}
        for rating in self.filtered(lambda act: act.res_model and act.res_id):
            if rating.res_model not in data_by_model:
                data_by_model[rating.res_model] = {
                    'ratings': self.env['rating.rating'],
                    'record_ids': [],
                }
            data_by_model[rating.res_model]['ratings'] += rating
            data_by_model[rating.res_model]['record_ids'].append(rating.res_id)
        return data_by_model

    def _to_store(self, store: Store, /, *, fields=None):
        if fields is None:
            fields = ["rating", "rating_image_url", "rating_text"]
        store.add(self._name, self._read_format(fields, load=False))
