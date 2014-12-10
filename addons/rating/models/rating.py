# -*- coding: utf-8 -*-
import logging
import uuid

from openerp import api, fields, models, _

_logger = logging.getLogger(__name__)


class Rating(models.Model):
    _name = "rating.rating"
    _description = "Rating"
    _order = 'create_date desc'
    _rec_name = 'res_name'
    _sql_constraints = [
            ('rating_range', 'check(rating >= -1 and rating <= 10)', 'Rating should be between -1 to 10'),
    ]

    @api.multi
    @api.depends('res_model', 'res_id')
    def _compute_res_name(self):
        for record in self:
            name = self.env[record.res_model].browse(record.res_id).name_get()
            record.res_name = name and name[0][1] or ('%s/%s') % (record.res_model, record.res_id)

    res_name = fields.Char(compute='_compute_res_name', string='Resource Name', store=True)
    res_model = fields.Char(string='Resource Model', required=True)
    res_id = fields.Integer(string='Resource ID', required=True)
    user_id = fields.Many2one('res.users', string='Rated User')
    customer_id = fields.Many2one('res.partner', string='Customer')
    rating = fields.Float(string="Rating", group_operator="avg", default=-1)

    @api.model
    def new_access_token(self):
        return uuid.uuid4().hex

    access_token = fields.Char(string='Security Token', default=new_access_token)

    @api.model
    def apply_rating(self, rating_state, res_model=None, res_id=None, token=None):
        """ apply a rating for given res_model and res_id (or token) and
            post a message in chatter of given res_id and res_model.
            :param integer res_id : id.
            :param string res_model : name of model.
            :param string token : access token
            :return recordset of relevant model
        """
        domain = [('access_token', '=', token)] if token else [
            ('res_model', '=', res_model), ('res_id', '=', res_id)]
        rating = self.env['rating.rating'].sudo().search(domain, limit=1)
        if rating:
            rating.rating = float(rating_state)
            if hasattr(self.env[rating.res_model], 'message_post'):
                record = self.env[rating.res_model].sudo().browse(rating.res_id)
                record.message_post(
                    body="%s %s <br/><img src='rating/static/src/img/rating_%s.png' style='width:20px;height:20px'/>"
                    % (record.partner_id.name, _('rated it'), rating_state))
            return record
        return False


class RatingMixin(models.AbstractModel):
    _name = 'rating.mixin'
    _description = "Rating Mixin"

    rating_ids = fields.One2many('rating.rating', 'res_id',
                                 domain=lambda self: [('res_model', '=', self._name)],
                                 string='Rating')
    @api.model
    def rating_send_request(self, template, template_res_id=None, partner_id=None, user_id=None):
        """
            Sends an email to the customer requesting rating
            for the Model's object from which it is called.
        """
        email_to = partner_id and partner_id.email or False
        rating_obj = self.env['rating.rating']
        if email_to and user_id.email:
            rating = rating_obj.search(
                [('res_id', '=', self.id), ('res_model', '=', self._name)])
            if not rating:
                rating = rating_obj.create({'res_model': self._name, 'res_id': self.id, 'user_id':
                                            user_id and user_id.id or False, 'customer_id': partner_id and partner_id.id or False})
            else:
                rating.write({'rating': -1, 'access_token': rating.new_access_token()})
            template.with_context(
                access_token=rating.access_token,
                model=self,
                model_name=rating.res_model,
                email_to=email_to
            ).send_mail(template_res_id, force_send=True)

    @api.multi
    def rating_get_repartition_per_value(self, res_ids=None, res_model=None):
        """ get the repatition of rating grade for the given res_ids.
            :param list res_ids : optional list of ids. If not given, this will take the ids of the current recordset.
            :param string res_model : optional name of model. If not given, the one of the current recordset will be used.
            :return dictionnary where the key is the rating value (the note), and the value, the number of object (res_model, res_id) having the value
        """
        if res_model is None:
            res_model = self._name
        if res_ids is None:
            res_ids = self.ids
        data = self.env['rating.rating'].read_group([('res_model', '=', res_model), (
            'res_id', 'in', res_ids), ('rating', '>=', 0)], ['rating'], ['rating', 'res_id'])
        # init dict with all posible rate value, except -1 (no value for the rating)
        res = dict.fromkeys(range(11), 0)
        res.update((d['rating'], d['rating_count']) for d in data)
        return res

    @api.multi
    def rating_get_repartition_per_grade(self, res_ids=None, res_model=None):
        """ get the repatition of rating grade for the given res_ids.
            :param list res_ids : optional list of ids. If not given, this will take the ids of the current recordset.
            :param string res_model : optional name of model. If not given, the one of the current recordset will be used.
            :return dictionnary where the key is the grade (great, okay, bad), and the value, the number of object (res_model, res_id) having the grade
                    the grade are compute as    0-30% : Bad
                                                31-69%: Okay
                                                70-100%: Great
        """
        if res_model is None:
            res_model = self._name
        if res_ids is None:
            res_ids = self.ids
        data = self.rating_get_repartition_per_value(res_ids, res_model)
        res = dict.fromkeys(['great', 'okay', 'bad'], 0)
        for key in data:
            if key >= 7:
                res['great'] += data[key]
            elif key > 3:
                res['okay'] += data[key]
            else:
                res['bad'] += data[key]
        return res
