# -*- coding: utf-8 -*-
import uuid
from openerp import api, fields, models, _

class Rating(models.Model):

    _name = "rating.rating"
    _description = "Rating"
    _order = 'create_date desc'
    _rec_name = 'res_name'
    _sql_constraints = [
        ('rating_range', 'check(rating >= -1 and rating <= 10)', 'Rating should be between -1 to 10'),
    ]

    @api.one
    @api.depends('res_model', 'res_id')
    def _compute_res_name(self):
        name = self.env[self.res_model].sudo().browse(self.res_id).name_get()
        self.res_name = name and name[0][1] or ('%s/%s') % (self.res_model, self.res_id)

    @api.model
    def new_access_token(self):
        return uuid.uuid4().hex

    res_name = fields.Char(string='Resource Name', compute='_compute_res_name', store=True, help="The name of the rated ressource.")
    res_model = fields.Char(string='Document Model', required=True, help="Model name of the rated object", index=True)
    res_id = fields.Integer(string='Document ID', required=True, help="Identifier of the rated object", index=True)
    rated_partner_id = fields.Many2one('res.partner', string="Rated Partner", help="Owner of the rated ressource")
    partner_id = fields.Many2one('res.partner', string='Customer', help="Author of the rating")
    rating = fields.Float(string="Rating", group_operator="avg", default=-1, help="Rating value")
    feedback = fields.Text('Feedback reason', help="Reason of the rating")
    access_token = fields.Char(string='Security Token', default=new_access_token, help="Access token to set the rating of the value")

    message_id = fields.Many2one('mail.message', string="Linked message", help="Associated message when posting a review. Mainly used in website addons.", index=True)

    @api.model
    def apply_rating(self, rate, res_model=None, res_id=None, token=None):
        """ apply a rating for given res_model/res_id or token. If the res_model is a mail.thread
            object, a message will be posted in the chatter.
            :param rate : the rating value to apply
            :type rate : float
            :param res_id : id of the rated object.
            :param res_model : name of model.
            :param token : access token
            :returns rating.rating record
        """
        domain = [('access_token', '=', token)] if token else [('res_model', '=', res_model), ('res_id', '=', res_id)]
        rating = self.search(domain, limit=1)
        if rating:
            if token:
                rating = rating.sudo()
            rating.write({'rating' : rate})
            if hasattr(self.env[rating.res_model], 'message_post'):
                record = self.env[rating.res_model].sudo().browse(rating.res_id)
                record.sudo().message_post(
                    body="%s %s <br/><img src='/rating/static/src/img/rating_%s.png' style='width:20px;height:20px'/>"
                    % (rating.sudo().partner_id.name, _('rated it'), rate),
                    subtype='mail.mt_comment',
                    author_id=rating.partner_id and rating.partner_id.id or None # None will set the default author in mail_thread.py
                )
        return rating

    @api.multi
    def reset(self):
        for record in self:
            record.write({
                'rating': -1,
                'access_token': record.new_access_token(),
                'feedback' : False
            })


class RatingMixin(models.AbstractModel):

    _name = 'rating.mixin'
    _description = "Rating Mixin"

    rating_ids = fields.One2many('rating.rating', 'res_id', string='Rating', domain=lambda self: [('res_model', '=', self._name)])

    @api.multi
    def rating_send_request(self, template, partner_id, rated_partner_id, reuse_rating=True):
        """ This method create (empty) rating objects for the current recordsets
            and send this request by mail (given email template) with the given
            rated_partner_id and partner_id as recipient and sender of the email.
            :param template : the email template to send. The res_model of the
                template  must be 'rating.rating'.
            :type template : mail.template
            :param res_model : model name of the object to rated_partner_id
            :type res_model : string
            :param res_id : id the record to rate
            :type res_id : int
            :param partner_id : the recipient partner
            :type partner : res.partner
            :param rated_partner_id : the sender partner
            :type rated_partner_id : res.partner
            :param reuse_rating : if True, the rating of the current objects will
                be reset. Otherwise a new rating will be create
            :type reuse_rating : boolean
        """
        if not rated_partner_id.email or not partner_id.email:
            return False
        Rating = self.env['rating.rating']
        res_model = self._name
        for record in self:
            res_id = record.id
            values = {
                'res_model': res_model,
                'res_id': res_id,
                'partner_id': partner_id.id,
                'rated_partner_id': rated_partner_id.id
            }
            if reuse_rating:
                # search the existing rating for the given res_model/res_id
                rating = Rating.search([('res_id', '=', res_id), ('res_model', '=', res_model), ('partner_id', '=', partner_id.id)], limit=1)
                if rating: # reset the rating
                    rating.reset()
                else: # create a new one
                    rating = Rating.create(values)
            else:
                rating = Rating.create(values)
            # send the mail
            template.send_mail(rating.id, force_send=True)

    @api.multi
    def rating_get_repartition(self, add_stats=False, domain=None):
        """ get the repatition of rating grade for the given res_ids.
            :param add_stats : flag to add stat to the result
            :type add_stats : boolean
            :param domain : optional extra domain of the rating to include/exclude in repartition
            :return dictionnary
                if not add_stats, the dict is like
                    - key is the rating value (integer)
                    - value is the number of object (res_model, res_id) having the value
                otherwise, key is the value of the information (string) : either stat name (avg, total, ...) or 'repartition'
                containing the same dict if add_stats was False.
        """
        base_domain = [('res_model', '=', self._name), ('res_id', 'in', self.ids), ('rating', '>=', 0)]
        if domain:
            base_domain += domain
        data = self.env['rating.rating'].read_group(base_domain, ['rating'], ['rating', 'res_id'])
        # init dict with all posible rate value, except -1 (no value for the rating)
        values = dict.fromkeys(range(11), 0)
        values.update((d['rating'], d['rating_count']) for d in data)
        # add other stats
        if add_stats:
            rating_number = sum(values.values())
            result = {
                'repartition': values,
                'avg': sum([float(key*values[key]) for key in values])/rating_number if rating_number > 0 else 0,
                'total': reduce(lambda x, y: y['rating_count']+x, data, 0),
            }
            return result
        return values

    @api.multi
    def rating_get_grades(self, domain=None):
        """ get the repatition of rating grade for the given res_ids.
            :param domain : optional domain of the rating to include/exclude in grades computation
            :return dictionnary where the key is the grade (great, okay, bad), and the value, the number of object (res_model, res_id) having the grade
                    the grade are compute as    0-30% : Bad
                                                31-69%: Okay
                                                70-100%: Great
        """
        data = self.rating_get_repartition(domain=domain)
        res = dict.fromkeys(['great', 'okay', 'bad'], 0)
        for key in data:
            if key >= 7:
                res['great'] += data[key]
            elif key > 3:
                res['okay'] += data[key]
            else:
                res['bad'] += data[key]
        return res

    @api.multi
    def rating_get_stats(self, domain=None):
        """ get the statistics of the rating repatition
            :param domain : optional domain of the rating to include/exclude in statistic computation
            :return dictionnary where
                - key is the the name of the information (stat name)
                - value is statistic value : 'percent' contains the repartition in percentage, 'avg' is the average rate
                  and 'total' is the number of rating
        """
        data = self.rating_get_repartition(domain=domain, add_stats=True)
        result = {
            'avg': data['avg'],
            'total': data['total'],
            'percent': dict.fromkeys(range(11), 0),
        }
        for rate in data['repartition']:
            result['percent'][rate] = (data['repartition'][rate] * 100) / data['total'] if data['total'] > 0 else 0
        return result
