# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import api, fields, models, _

EMAIL_PATTERN = '([^ ,;<@]+@[^> ,;]+)'

class MailBlackList(models.Model):
    """ Model of blacklisted email addresses to stop sending emails."""
    _name = 'mail.mass_mailing.blacklist'
    _inherit = ['mail.thread']
    _description = 'Mail Blacklist'
    _rec_name = 'email'

    email = fields.Char(string='Email Address', required=True, index=True)
    active = fields.Boolean(default=True)
    reason = fields.Char()

    _sql_constraints = [
        ('unique_email', 'unique (email)', 'Email address already exists!')
    ]

    @api.multi
    def write(self, vals):
        result = super(MailBlackList, self).write(vals)
        if 'active' in vals:
            if vals['active']:
                for rec in self:
                    message = 'The email address %s has been blacklisted.' % rec.email
                    if rec.reason:
                        message += ' %s' % rec.reason
                    self._message_log(body=_(message), message_type='comment')
            else:
                for rec in self:
                    self._message_log(body=_('The email address %s has been removed from blacklist.' % rec.email), message_type='comment')
        return result

    def _toggle_blacklist(self, email, source, action_from_recipient):
        blacklist = self.env["mail.mass_mailing.blacklist"].sudo()
        record = blacklist.with_context(active_test=False).search([('email', '=', email)])
        if len(record) > 0:
            if record.active:
                record.write({
                    'active': False,
                    'reason': ''
                })
                return False
            else:
                reason = 'The recipient has added himself to the blacklist using the unsubscription page.' \
                    if action_from_recipient else "%s has blacklisted the recipient from %s." % \
                                                  (self.env['res.users'].browse(self._uid).name, source)
                record.write({
                    'active': True,
                    'reason': reason
                })
        else:
            reason = 'The recipient has added himself to the blacklist using the unsubscription page.' \
                if action_from_recipient else "%s has blacklisted the recipient from %s." % \
                                              (self.env['res.users'].browse(self._uid).name, source)
            record = self.create({
                'email': email,
                'reason': reason,
            })
            message = 'The email address %s has been blacklisted.' % email
            if reason:
                message += ' %s' % reason
            record._message_log(body=_(message), message_type='comment')
        return True


class MailBlackListMixin(models.Model):
    """ Mixin that is inherited by all model with opt out.
        USAGE : the method '_blacklist_get_email_field_name' must be overridden in the model that inherit the mixin
        and must contain the email field of the model.
        """
    _name = 'mail.mass_mailing.blacklist.mixin'
    _description = 'Mail Blacklist mixin'

    # method that will be overriden in the model that inherit the mixin
    # to know on which field the _compute_is_blacklisted() must depend
    def _blacklist_get_email_field_name(self):
        return []

    # Creates the depends expression to work with two fields, one known and one from model that inherit the mixin.
    def _blacklist_get_depends(self):
        if self._blacklist_get_email_field_name():
            [email_field] = self._blacklist_get_email_field_name()
            return ['blacklist_id.active', email_field]
        else:
            return ['blacklist_id.active']

    # blacklist_id creates an explicit link to the blacklist model
    # in order to know which email in model that inherits the mixin is impacted by changes in blacklist model.
    # an non stored fields cannot be used as dependence
    # except if there is a search method on it (that inverse the many2one dependence)
    # so each time the blacklist is modified 'created, deleted or set to active/inactive,
    # the blacklist_id of the impacted records is re_computed and the is_blacklist field too
    blacklist_id = fields.Many2one('mail.mass_mailing.blacklist', store=False, search="_blacklist_search_blacklist_id",
                                   string='Blacklist id')

    # Note :
    # With store = False, the access to the field is not evaluated because the fields is not in DB.
    # With store = True, the access to the field can be evaluated.
    is_blacklisted = fields.Boolean(string='Blacklist', compute="_blacklist_compute_is_blacklisted", store=True,
        help="If the email address is on the blacklist, the contact won't receive mass mailing anymore, from any list",
        groups="base.group_user")
    blacklist_reason = fields.Char(compute="_blacklist_compute_is_blacklisted", store=True)

    @api.model
    def _blacklist_search_blacklist_id(self, operator, value):
        if self._blacklist_get_email_field_name():
            [email_field] = self._blacklist_get_email_field_name()
            # implement search with domain [('blacklist_id', 'in', value)]
            assert operator == 'in' and isinstance(value, list)
            black_recs = self.env['mail.mass_mailing.blacklist'].browse(value)
            emails = black_recs.mapped('email')
            return [(email_field, 'in', emails)]
        # else:
        #     return []

    @api.depends(lambda self: self._blacklist_get_depends())
    def _blacklist_compute_is_blacklisted(self):
        [email_field] = self._blacklist_get_email_field_name()
        blacklist = self.env['mail.mass_mailing.blacklist'].sudo().search([('email', 'in', [item[email_field] for item in self])]).read(['email', 'reason', 'active'])
        for rec in self:  # Optimisation: create indexed dict sorted by email and lookup in dict to get email and reason
            email = rec[email_field]
            item = next((x for x in blacklist if email == x['email']), None)
            rec.is_blacklisted = bool(item['active']) if item else False
            rec.blacklist_reason = str(item['reason']) if item and item['reason'] else ''

    @api.multi
    def toggle_blacklist(self):
        [email_field] = self._blacklist_get_email_field_name()
        self.ensure_one()
        email = self[email_field]
        if email and re.match(EMAIL_PATTERN, email):
            if self.env["mail.mass_mailing.blacklist"].sudo()._toggle_blacklist(email, self._description, False):
                return [self.id, True]
            else:
                return [self.id, False]
        return [self.id, 'not_found']
