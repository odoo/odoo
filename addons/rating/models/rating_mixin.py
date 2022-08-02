# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import operator

from odoo import api, fields, models, tools
from odoo.addons.rating.models import rating_data
from odoo.osv import expression
from odoo.tools.float_utils import float_compare, float_round


class RatingMixin(models.AbstractModel):
    _name = 'rating.mixin'
    _description = "Rating Mixin"

    rating_ids = fields.One2many('rating.rating', 'res_id', string='Rating', groups='base.group_user', domain=lambda self: [('res_model', '=', self._name)], auto_join=True)
    rating_last_value = fields.Float('Rating Last Value', groups='base.group_user', compute='_compute_rating_last_value', compute_sudo=True, store=True)
    rating_last_feedback = fields.Text('Rating Last Feedback', groups='base.group_user', related='rating_ids.feedback')
    rating_last_image = fields.Binary('Rating Last Image', groups='base.group_user', related='rating_ids.rating_image')
    rating_count = fields.Integer('Rating count', compute="_compute_rating_stats", compute_sudo=True)
    rating_avg = fields.Float("Average Rating", groups='base.group_user',
        compute='_compute_rating_stats', compute_sudo=True, search='_search_rating_avg')
    rating_avg_text = fields.Selection(rating_data.RATING_TEXT, groups='base.group_user',
        compute='_compute_rating_avg_text', compute_sudo=True)
    rating_percentage_satisfaction = fields.Float("Rating Satisfaction", compute='_compute_rating_satisfaction', compute_sudo=True)
    rating_last_text = fields.Selection(string="Rating Text", groups='base.group_user', related="rating_ids.rating_text")

    @api.depends('rating_ids.rating', 'rating_ids.consumed')
    def _compute_rating_last_value(self):
        # Pure SQL instead of calling read_group to allow ordering array_agg
        self.flush_model(['rating_ids'])
        self.env['rating.rating'].flush_model(['consumed', 'rating'])
        if not self.ids:
            self.rating_last_value = 0
            return
        self.env.cr.execute("""
            SELECT
                array_agg(rating ORDER BY write_date DESC, id DESC) AS "ratings",
                res_id as res_id
            FROM "rating_rating"
            WHERE
                res_model = %s
            AND res_id in %s
            AND consumed = true
            GROUP BY res_id""", [self._name, tuple(self.ids)])
        read_group_raw = self.env.cr.dictfetchall()
        rating_by_res_id = {e['res_id']: e['ratings'][0] for e in read_group_raw}
        for record in self:
            record.rating_last_value = rating_by_res_id.get(record.id, 0)

    @api.depends('rating_ids.res_id', 'rating_ids.rating')
    def _compute_rating_stats(self):
        """ Compute avg and count in one query, as thoses fields will be used together most of the time. """
        domain = expression.AND([self._rating_domain(), [('rating', '>=', rating_data.RATING_LIMIT_MIN)]])
        read_group_res = self.env['rating.rating'].read_group(domain, ['rating:avg'], groupby=['res_id'], lazy=False)  # force average on rating column
        mapping = {item['res_id']: {'rating_count': item['__count'], 'rating_avg': item['rating']} for item in read_group_res}
        for record in self:
            record.rating_count = mapping.get(record.id, {}).get('rating_count', 0)
            record.rating_avg = mapping.get(record.id, {}).get('rating_avg', 0)

    def _search_rating_avg(self, operator, value):
        if operator not in rating_data.OPERATOR_MAPPING:
            raise NotImplementedError('This operator %s is not supported in this search method.' % operator)
        rating_read_group = self.env['rating.rating'].sudo().read_group(
            [('res_model', '=', self._name), ('consumed', '=', True), ('rating', '>=', rating_data.RATING_LIMIT_MIN)],
            ['res_id', 'rating_avg:avg(rating)'], ['res_id'])
        res_ids = [
            res['res_id']
            for res in rating_read_group
            if rating_data.OPERATOR_MAPPING[operator](float_compare(res['rating_avg'], value, 2), 0)
        ]
        return [('id', 'in', res_ids)]

    @api.depends('rating_avg')
    def _compute_rating_avg_text(self):
        for record in self:
            record.rating_avg_text = rating_data._rating_avg_to_text(record.rating_avg)

    @api.depends('rating_ids.res_id', 'rating_ids.rating')
    def _compute_rating_satisfaction(self):
        """ Compute the rating satisfaction percentage, this is done separately from rating_count and rating_avg
            since the query is different, to avoid computing if it is not necessary"""
        domain = expression.AND([self._rating_domain(), [('rating', '>=', rating_data.RATING_LIMIT_MIN)]])
        # See `_compute_rating_percentage_satisfaction` above
        read_group_res = self.env['rating.rating']._read_group(domain, ['res_id', 'rating'], groupby=['res_id', 'rating'], lazy=False)
        default_grades = {'great': 0, 'okay': 0, 'bad': 0}
        grades_per_record = {record_id: default_grades.copy() for record_id in self.ids}

        for group in read_group_res:
            record_id = group['res_id']
            grade = rating_data._rating_to_grade(group['rating'])
            grades_per_record[record_id][grade] += group['__count']

        for record in self:
            grade_repartition = grades_per_record.get(record.id, default_grades)
            grade_count = sum(grade_repartition.values())
            record.rating_percentage_satisfaction = grade_repartition['great'] * 100 / grade_count if grade_count else -1

    def write(self, values):
        """ If the rated ressource name is modified, we should update the rating res_name too.
            If the rated ressource parent is changed we should update the parent_res_id too"""
        with self.env.norecompute():
            result = super(RatingMixin, self).write(values)
            for record in self:
                if record._rec_name in values:  # set the res_name of ratings to be recomputed
                    res_name_field = self.env['rating.rating']._fields['res_name']
                    self.env.add_to_compute(res_name_field, record.rating_ids)
                if record._rating_get_parent_field_name() in values:
                    record.rating_ids.sudo().write({'parent_res_id': record[record._rating_get_parent_field_name()].id})

        return result

    def unlink(self):
        """ When removing a record, its rating should be deleted too. """
        record_ids = self.ids
        result = super(RatingMixin, self).unlink()
        self.env['rating.rating'].sudo().search([('res_model', '=', self._name), ('res_id', 'in', record_ids)]).unlink()
        return result

    def _rating_get_parent_field_name(self):
        """Return the parent relation field name
           Should return a Many2One"""
        return None

    def _rating_domain(self):
        """ Returns a normalized domain on rating.rating to select the records to
            include in count, avg, ... computation of current model.
        """
        return ['&', '&', ('res_model', '=', self._name), ('res_id', 'in', self.ids), ('consumed', '=', True)]

    def _rating_get_partner(self):
        """ Return the customer (partner) that performs the rating.

        :return record: res.partner singleton
        """
        if hasattr(self, 'partner_id') and self.partner_id:
            return self.partner_id
        return self.env['res.partner']

    def _rating_get_operator(self):
        """ Return the operator (partner) that is the person who is rated.

        :return record: res.partner singleton
        """
        if hasattr(self, 'user_id') and self.user_id.partner_id:
            return self.user_id.partner_id
        return self.env['res.partner']

    def _rating_get_access_token(self, partner=None):
        """ Return access token linked to existing ratings, or create a new rating
        that will create the asked token. An explicit call to access rights is
        performed as sudo is used afterwards as this method could be used from
        different sources, notably templates. """
        self.check_access_rights('read')
        self.check_access_rule('read')
        if not partner:
            partner = self._rating_get_partner()
        rated_partner = self._rating_get_operator()
        ratings = self.rating_ids.sudo().filtered(lambda x: x.partner_id.id == partner.id and not x.consumed)
        if not ratings:
            rating = self.env['rating.rating'].sudo().create({
                'partner_id': partner.id,
                'rated_partner_id': rated_partner.id,
                'res_model_id': self.env['ir.model']._get_id(self._name),
                'res_id': self.id,
                'is_internal': False,
            })
        else:
            rating = ratings[0]
        return rating.access_token

    def rating_send_request(self, template, lang=False, subtype_id=False, force_send=True, composition_mode='comment',
                            email_layout_xmlid=None):
        """ This method send rating request by email, using a template given
        in parameter.

         :param record template: a mail.template record used to compute the message body;
         :param str lang: optional lang; it can also be specified directly on the template
           itself in the lang field;
         :param int subtype_id: optional subtype to use when creating the message; is
           a note by default to avoid spamming followers;
         :param bool force_send: whether to send the request directly or use the mail
           queue cron (preferred option);
         :param str composition_mode: comment (message_post) or mass_mail (template.send_mail);
         :param str email_layout_xmlid: layout used to encapsulate the content when sending email;
        """
        if lang:
            template = template.with_context(lang=lang)
        if subtype_id is False:
            subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note')
        if force_send:
            self = self.with_context(mail_notify_force_send=True)  # default value is True, should be set to false if not?
        for record in self:
            record.message_post_with_template(
                template.id,
                composition_mode=composition_mode,
                email_layout_xmlid=email_layout_xmlid if email_layout_xmlid is not None else 'mail.mail_notification_light',
                subtype_id=subtype_id
            )

    def rating_apply(self, rate, token=None, rating=None, feedback=None, subtype_xmlid=None):
        """ Apply a rating to the record. This rating can either be linked to a
        token (customer flow) or directly a rating record (code flow).

        If the current model inherits from mail.thread mixin a message is posted
        on its chatter. User going through this method should have at least
        employee rights as well as rights on the current record because of rating
        manipulation and chatter post (either employee, either sudo-ed in public
        controllers after security check granting access).

        :param float rate: the rating value to apply (from 0 to 5);
        :param string token: access token to fetch the rating to apply (optional);
        :param record rating: rating.rating to apply (if no token);
        :param string feedback: additional feedback (plaintext);
        :param string subtype_xmlid: xml id of a valid mail.message.subtype used
          to post the message (if it applies). If not given a classic comment is
          posted;

        :returns rating: rating.rating record
        """
        if rate < 0 or rate > 5:
            raise ValueError('Wrong rating value. A rate should be between 0 and 5 (received %d).' % rate)
        if token:
            rating = self.env['rating.rating'].search([('access_token', '=', token)], limit=1)
        if not rating:
            raise ValueError('Invalid token or rating.')

        rating.write({'rating': rate, 'feedback': feedback, 'consumed': True})
        if hasattr(self, 'message_post'):
            if subtype_xmlid is None:
                subtype_id = self._rating_apply_get_default_subtype_id()
            else:
                subtype_id = self.env['ir.model.data']._xmlid_to_res_id(subtype_xmlid)
            feedback = tools.plaintext2html(feedback or '')
            self.message_post(
                author_id=rating.partner_id.id or None,  # None will set the default author in mail_thread.py
                body="<img src='%s' alt=':%s/5' style='width:18px;height:18px;float:left;margin-right: 5px;'/>%s"
                % (rating.rating_image_url, rate, feedback),
                rating_id=rating.id,
                subtype_id=subtype_id,
            )
        return rating

    def _rating_apply_get_default_subtype_id(self):
        return self.env['ir.model.data']._xmlid_to_res_id("mail.mt_comment")

    def _rating_get_repartition(self, add_stats=False, domain=None):
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
        base_domain = expression.AND([self._rating_domain(), [('rating', '>=', 1)]])
        if domain:
            base_domain += domain
        rg_data = self.env['rating.rating'].read_group(base_domain, ['rating'], ['rating', 'res_id'])
        # init dict with all posible rate value, except 0 (no value for the rating)
        values = dict.fromkeys(range(1, 6), 0)
        for rating_rg in rg_data:
            rating_val_round = float_round(rating_rg['rating'], precision_digits=1)
            values[rating_val_round] = values.get(rating_val_round, 0) + rating_rg['rating_count']
        # add other stats
        if add_stats:
            rating_number = sum(values.values())
            result = {
                'repartition': values,
                'avg': sum(float(key * values[key]) for key in values) / rating_number if rating_number > 0 else 0,
                'total': sum(it['rating_count'] for it in rg_data),
            }
            return result
        return values

    def rating_get_grades(self, domain=None):
        """ get the repatition of rating grade for the given res_ids.
            :param domain : optional domain of the rating to include/exclude in grades computation
            :return dictionnary where the key is the grade (great, okay, bad), and the value, the number of object (res_model, res_id) having the grade
                    the grade are compute as    0-30% : Bad
                                                31-69%: Okay
                                                70-100%: Great
        """
        data = self._rating_get_repartition(domain=domain)
        res = dict.fromkeys(['great', 'okay', 'bad'], 0)
        for key in data:
            grade = rating_data._rating_to_grade(key)
            res[grade] += data[key]
        return res

    def rating_get_stats(self, domain=None):
        """ get the statistics of the rating repatition
            :param domain : optional domain of the rating to include/exclude in statistic computation
            :return dictionnary where
                - key is the name of the information (stat name)
                - value is statistic value : 'percent' contains the repartition in percentage, 'avg' is the average rate
                  and 'total' is the number of rating
        """
        data = self._rating_get_repartition(domain=domain, add_stats=True)
        result = {
            'avg': data['avg'],
            'total': data['total'],
            'percent': dict.fromkeys(range(1, 6), 0),
        }
        for rate in data['repartition']:
            result['percent'][rate] = (data['repartition'][rate] * 100) / data['total'] if data['total'] > 0 else 0
        return result
