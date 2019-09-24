# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import uuid

from datetime import timedelta

from odoo import api, fields, models, tools, _

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

    @api.one
    @api.depends('res_model', 'res_id')
    def _compute_res_name(self):
        name = self.env[self.res_model].sudo().browse(self.res_id).name_get()
        self.res_name = name and name[0][1] or ('%s/%s') % (self.res_model, self.res_id)

    @api.model
    def new_access_token(self):
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
    access_token = fields.Char('Security Token', default=new_access_token, help="Access token to set the rating of the value")
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
        # Due to some new widgets, we may have ratings different from 0/1/5/10 (e.g. slide.channel review)
        # Let us have some custom rounding while finding a better solution for images.
        for rating in self:
            rating_for_img = 0
            if rating.rating >= 8:
                rating_for_img = 10
            elif rating.rating > 3:
                rating_for_img = 5
            elif rating.rating >= 1:
                rating_for_img = 1
            try:
                image_path = get_resource_path('rating', 'static/src/img', 'rating_%s.png' % rating_for_img)
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
        if hasattr(current_record, 'rating_get_parent'):
            current_record_parent = current_record.rating_get_parent()
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
                'access_token': record.new_access_token(),
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


class RatingMixin(models.AbstractModel):
    _name = 'rating.mixin'
    _description = "Rating Mixin"

    rating_ids = fields.One2many('rating.rating', 'res_id', string='Rating', domain=lambda self: [('res_model', '=', self._name)], auto_join=True)
    rating_last_value = fields.Float('Rating Last Value', compute='_compute_rating_last_value', compute_sudo=True, store=True)
    rating_last_feedback = fields.Text('Rating Last Feedback', related='rating_ids.feedback', readonly=False)
    rating_last_image = fields.Binary('Rating Last Image', related='rating_ids.rating_image', readonly=False)
    rating_count = fields.Integer('Rating count', compute="_compute_rating_count")

    @api.multi
    @api.depends('rating_ids.rating')
    def _compute_rating_last_value(self):
        for record in self:
            ratings = self.env['rating.rating'].search([('res_model', '=', self._name), ('res_id', '=', record.id)], limit=1)
            if ratings:
                record.rating_last_value = ratings.rating

    @api.multi
    @api.depends('rating_ids')
    def _compute_rating_count(self):
        read_group_res = self.env['rating.rating'].read_group(
            [('res_model', '=', self._name), ('res_id', 'in', self.ids), ('consumed', '=', True)],
            ['res_id'], groupby=['res_id'])
        result = dict.fromkeys(self.ids, 0)
        for data in read_group_res:
            result[data['res_id']] += data['res_id_count']
        for record in self:
            record.rating_count = result.get(record.id)

    def write(self, values):
        """ If the rated ressource name is modified, we should update the rating res_name too.
            If the rated ressource parent is changed we should update the parent_res_id too"""
        with self.env.norecompute():
            result = super(RatingMixin, self).write(values)
            for record in self:
                if record._rec_name in values:  # set the res_name of ratings to be recomputed
                    res_name_field = self.env['rating.rating']._fields['res_name']
                    record.rating_ids._recompute_todo(res_name_field)
                if record.rating_get_parent() in values:
                    record.rating_ids.write({'parent_res_id': record[record.rating_get_parent()].id})

        if self.env.recompute and self._context.get('recompute', True):  # trigger the recomputation of all field marked as "to recompute"
            self.recompute()

        return result

    def unlink(self):
        """ When removing a record, its rating should be deleted too. """
        record_ids = self.ids
        result = super(RatingMixin, self).unlink()
        self.env['rating.rating'].sudo().search([('res_model', '=', self._name), ('res_id', 'in', record_ids)]).unlink()
        return result

    def rating_get_parent(self):
        """Return the parent relation field name
           Should return a Many2One"""
        return None

    def rating_get_partner_id(self):
        if hasattr(self, 'partner_id') and self.partner_id:
            return self.partner_id
        return self.env['res.partner']

    def rating_get_rated_partner_id(self):
        if hasattr(self, 'user_id') and self.user_id.partner_id:
            return self.user_id.partner_id
        return self.env['res.partner']

    def rating_get_access_token(self, partner=None):
        if not partner:
            partner = self.rating_get_partner_id()
        rated_partner = self.rating_get_rated_partner_id()
        ratings = self.rating_ids.filtered(lambda x: x.partner_id.id == partner.id and not x.consumed)
        if not ratings:
            record_model_id = self.env['ir.model'].sudo().search([('model', '=', self._name)], limit=1).id
            rating = self.env['rating.rating'].create({
                'partner_id': partner.id,
                'rated_partner_id': rated_partner.id,
                'res_model_id': record_model_id,
                'res_id': self.id
            })
        else:
            rating = ratings[0]
        return rating.access_token

    @api.multi
    def rating_send_request(self, template, lang=False, subtype_id=False, force_send=True, composition_mode='comment', notif_layout=None):
        """ This method send rating request by email, using a template given
        in parameter.

         :param template: a mail.template record used to compute the message body;
         :param lang: optional lang; it can also be specified directly on the template
           itself in the lang field;
         :param subtype_id: optional subtype to use when creating the message; is
           a note by default to avoid spamming followers;
         :param force_send: whether to send the request directly or use the mail
           queue cron (preferred option);
         :param composition_mode: comment (message_post) or mass_mail (template.send_mail);
         :param notif_layout: layout used to encapsulate the content when sending email;
        """
        if lang:
            template = template.with_context(lang=lang)
        if subtype_id is False:
            subtype_id = self.env['ir.model.data'].xmlid_to_res_id('mail.mt_note')
        if force_send:
            self = self.with_context(mail_notify_force_send=True)
        for record in self:
            record.message_post_with_template(
                template.id,
                composition_mode=composition_mode,
                notif_layout=notif_layout if notif_layout is not None else 'mail.mail_notification_light',
                subtype_id=subtype_id
            )

    @api.multi
    def rating_apply(self, rate, token=None, feedback=None, subtype=None):
        """ Apply a rating given a token. If the current model inherits from
        mail.thread mixing, a message is posted on its chatter.
        :param rate : the rating value to apply
        :type rate : float
        :param token : access token
        :param feedback : additional feedback
        :type feedback : string
        :param subtype : subtype for mail
        :type subtype : string
        :returns rating.rating record
        """
        Rating, rating = self.env['rating.rating'], None
        if token:
            rating = self.env['rating.rating'].search([('access_token', '=', token)], limit=1)
        else:
            rating = Rating.search([('res_model', '=', self._name), ('res_id', '=', self.ids[0])], limit=1)
        if rating:
            rating.write({'rating': rate, 'feedback': feedback, 'consumed': True})
            if hasattr(self, 'message_post'):
                feedback = tools.plaintext2html(feedback or '')
                self.message_post(
                    body="<img src='/rating/static/src/img/rating_%s.png' alt=':%s/10' style='width:18px;height:18px;float:left;margin-right: 5px;'/>%s"
                    % (rate, rate, feedback),
                    subtype=subtype or "mail.mt_comment",
                    author_id=rating.partner_id and rating.partner_id.id or None  # None will set the default author in mail_thread.py
                )
            if hasattr(self, 'stage_id') and self.stage_id and hasattr(self.stage_id, 'auto_validation_kanban_state') and self.stage_id.auto_validation_kanban_state:
                if rating.rating > 5:
                    self.write({'kanban_state': 'done'})
                if rating.rating < 5:
                    self.write({'kanban_state': 'blocked'})
        return rating

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
        base_domain = [('res_model', '=', self._name), ('res_id', 'in', self.ids), ('rating', '>=', 1), ('consumed', '=', True)]
        if domain:
            base_domain += domain
        data = self.env['rating.rating'].read_group(base_domain, ['rating'], ['rating', 'res_id'])
        # init dict with all posible rate value, except 0 (no value for the rating)
        values = dict.fromkeys(range(1, 11), 0)
        values.update((d['rating'], d['rating_count']) for d in data)
        # add other stats
        if add_stats:
            rating_number = sum(values.values())
            result = {
                'repartition': values,
                'avg': sum(float(key * values[key]) for key in values) / rating_number if rating_number > 0 else 0,
                'total': sum(it['rating_count'] for it in data),
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
            if key >= RATING_LIMIT_SATISFIED:
                res['great'] += data[key]
            elif key > RATING_LIMIT_OK:
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
            'percent': dict.fromkeys(range(1, 11), 0),
        }
        for rate in data['repartition']:
            result['percent'][rate] = (data['repartition'][rate] * 100) / data['total'] if data['total'] > 0 else 0
        return result

    @api.model
    def _compute_parent_rating_percentage_satisfaction(self, parent_records, rating_satisfaction_days=None):
        # build domain and fetch data
        domain = [('parent_res_model', '=', parent_records._name), ('parent_res_id', 'in', parent_records.ids), ('rating', '>=', 1), ('consumed', '=', True)]
        if rating_satisfaction_days:
            domain += [('write_date', '>=', fields.Datetime.to_string(fields.datetime.now() - timedelta(days=rating_satisfaction_days)))]
        data = self.env['rating.rating'].read_group(domain, ['parent_res_id', 'rating'], ['parent_res_id', 'rating'], lazy=False)

        # get repartition of grades per parent id
        default_grades = {'great': 0, 'okay': 0, 'bad': 0}
        grades_per_parent = dict((parent_id, dict(default_grades)) for parent_id in parent_records.ids)  # map: {parent_id: {'great': 0, 'bad': 0, 'ok': 0}}
        for item in data:
            parent_id = item['parent_res_id']
            rating = item['rating']
            if rating >= RATING_LIMIT_SATISFIED:
                grades_per_parent[parent_id]['great'] += item['__count']
            elif rating > RATING_LIMIT_OK:
                grades_per_parent[parent_id]['okay'] += item['__count']
            else:
                grades_per_parent[parent_id]['bad'] += item['__count']

        # compute percentage per parent
        res = {}
        for record in parent_records:
            repartition = grades_per_parent.get(record.id)
            res[record.id] = repartition['great'] * 100 / sum(repartition.values()) if sum(repartition.values()) else -1
        return res
