# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import markupsafe

from odoo import _, fields, models, tools


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    rating_ids = fields.One2many('rating.rating', 'res_id', string='Ratings', groups='base.group_user',
                                 domain=lambda self: [('res_model', '=', self._name)], bypass_search_access=True)

    # MAIL OVERRIDES
    # --------------------------------------------------

    def unlink(self):
        """ When removing a record, its rating should be deleted too. """
        record_ids = self.ids
        result = super().unlink()
        self.env['rating.rating'].sudo().search([('res_model', '=', self._name), ('res_id', 'in', record_ids)]).unlink()
        return result

    def _get_message_create_ignore_field_names(self):
        return super()._get_message_create_ignore_field_names() | {"rating_id"}

    # RATING CONFIGURATION
    # --------------------------------------------------

    def _rating_apply_get_default_subtype_id(self):
        return self.env['ir.model.data']._xmlid_to_res_id("mail.mt_comment")

    def _rating_get_operator(self):
        """ Return the operator (partner) that is the person who is rated.

        :return: res.partner singleton
        """
        if 'user_id' in self and self.user_id.partner_id:
            return self.user_id.partner_id
        return self.env['res.partner']

    def _rating_get_partner(self):
        """ Return the customer (partner) that performs the rating.

        :return: res.partner singleton
        """
        if 'partner_id' in self and self.partner_id:
            return self.partner_id
        return self.env['res.partner']

    # RATING SUPPORT
    # --------------------------------------------------

    def _rating_get_access_token(self, partner=None):
        """ Return access token linked to existing ratings, or create a new rating
        that will create the asked token. An explicit call to access rights is
        performed as sudo is used afterwards as this method could be used from
        different sources, notably templates. """
        self.check_access('read')
        if not partner:
            partner = self._rating_get_partner()
        rated_partner = self._rating_get_operator()
        rating = next(
            (r for r in self.rating_ids.sudo()
             if r.partner_id.id == partner.id and not r.consumed),
            None)
        if not rating:
            rating = self.env['rating.rating'].sudo().create({
                'partner_id': partner.id,
                'rated_partner_id': rated_partner.id,
                'res_model_id': self.env['ir.model']._get_id(self._name),
                'res_id': self.id,
                'is_internal': False,
            })
        return rating.access_token

    # EXPOSED API
    # --------------------------------------------------

    def rating_send_request(self, template, lang=False, force_send=True):
        """ This method send rating request by email, using a template given in parameter.

         :param record template: a mail.template record used to compute the message body;
         :param str lang: optional lang; it can also be specified directly on the template
           itself in the lang field;
         :param bool force_send: whether to send the request directly or use the mail
           queue cron (preferred option);
        """
        if lang:
            template = template.with_context(lang=lang)
        self.with_context(mail_notify_force_send=force_send).message_post_with_source(
            template,
            email_layout_xmlid='mail.mail_notification_light',
            force_send=force_send,
            subtype_xmlid='mail.mt_note',
        )

    def rating_apply(self, rate, token=None, rating=None, feedback=None,
                     subtype_xmlid=None, notify_delay_send=False):
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
        :param notify_delay_send: Delay the sending by 2 hours of the email so the user
            can still change his feedback. If False, the email will be sent immediately.

        :returns: rating.rating record
        """
        if rate < 0 or rate > 5:
            raise ValueError(_('Wrong rating value. A rate should be between 0 and 5 (received %d).', rate))
        if token:
            rating = self.env['rating.rating'].search([('access_token', '=', token)], limit=1)
        if not rating:
            raise ValueError(_('Invalid token or rating.'))

        rating.write({'rating': rate, 'feedback': feedback, 'consumed': True})
        if isinstance(self, self.env.registry['mail.thread']):
            if subtype_xmlid is None:
                subtype_id = self._rating_apply_get_default_subtype_id()
            else:
                subtype_id = False
            feedback = tools.plaintext2html(feedback or '')

            scheduled_datetime = (
                fields.Datetime.now() + datetime.timedelta(hours=2)
                if notify_delay_send else None
            )
            rating_body = (
                    markupsafe.Markup(
                        "<img src='%s' alt=':%s/5' style='width:18px;height:18px;float:left;margin-right: 5px;'/>%s"
                    ) % (rating.rating_image_url, rate, feedback)
            )

            if rating.message_id:
                self._message_update_content(
                    rating.message_id,
                    body=rating_body,
                    scheduled_date=scheduled_datetime,
                    strict=False,
                )
            else:
                self.message_post(
                    author_id=rating.partner_id.id or None,  # None will set the default author in mail/mail_thread.py
                    body=rating_body,
                    rating_id=rating.id,
                    scheduled_date=scheduled_datetime,
                    subtype_id=subtype_id,
                    subtype_xmlid=subtype_xmlid,
                )
        return rating

    def message_post(self, **kwargs):
        rating_id = kwargs.pop('rating_id', False)
        rating_value = kwargs.pop('rating_value', False)
        # create rating.rating record linked to given rating_value. Using sudo as portal users may have
        # rights to create messages and therefore ratings (security should be checked beforehand)
        if rating_value:
            rating_vals = {
                'rating': float(rating_value) if rating_value is not None else False,
                'feedback': tools.html2plaintext(kwargs.get('body', '')),
                'res_model_id': self.env['ir.model']._get_id(self._name),
                'res_id': self.id,
                'consumed': True,
                'partner_id': self.env.user.partner_id.id,
            }
            rating_id = self.env["rating.rating"].sudo().create(rating_vals).id
        if rating_id:
            kwargs["rating_id"] = rating_id
        return super().message_post(**kwargs)

    def _message_post_after_hook(self, message, msg_values):
        """Override to link rating to message as sudo. This is done in
        _message_post_after_hook to be before _notify_thread."""
        # sudo: rating.rating - can link rating to message from same author and thread
        rating = self.env["rating.rating"].browse(msg_values.get("rating_id")).sudo()
        same_author = rating.partner_id and rating.partner_id == message.author_id
        if same_author and rating.res_model == message.model and rating.res_id == message.res_id:
            rating.message_id = message.id
        super()._message_post_after_hook(message, msg_values)

    def _get_allowed_message_params(self):
        return super()._get_allowed_message_params() | {"rating_value"}

    def _message_update_content(self, message, /, *, body, rating_value=None, **kwargs):
        if rating_value:
            message.rating_id.rating = rating_value
            message.rating_id.feedback = tools.html2plaintext(body)
        elif rating_value is False:
            rating_ids = message.rating_ids
            rating_ids.message_id = False
            rating_ids.unlink()
        return super()._message_update_content(message, body=body, **kwargs)
