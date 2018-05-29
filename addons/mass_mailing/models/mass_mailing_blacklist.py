# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import api, fields, models, _

EMAIL_PATTERN = '([^ ,;<@]+@[^> ,;]+)'

class MailBlackList(models.Model):
    """ Model of blacklisted email addresses to stop sending emails."""
    _name = 'mail.mass_mailing.blacklist'
    _description = 'Mail Blacklist'

    name = fields.Char(string='Name')
    email = fields.Char(string='Email Address', required=True, index=True)
    reason = fields.Char()
    company_id = fields.Many2one('res.company', string='Company Name')

    _sql_constraints = [
        ('unique_email', 'unique (email)', 'Email address already exists!')
    ]

    @api.model
    def create(self, vals):
        partner_ids = self.env['res.partner'].search([('email', '=ilike', vals['email'])])
        message = 'The email address %s has been blacklisted.' % vals['email']
        if 'reason' in vals:
            message += ' %s' % vals['reason']
        partner_ids.sudo().message_post(body=_(message))
        return super(MailBlackList, self).create(vals)

    @api.multi
    def unlink(self):
        # Better but the =ilike is lost
        partner_ids = self.env['res.partner'].search([('email', 'in', [rec.email for rec in self])])
        for rec in self:
            partners = partner_ids.filtered(lambda r: r.email == rec.email)
            if partners:
                partners.sudo().message_post(body=_('The email address %s has been removed from blacklist.') % (rec.email,))
        return super(MailBlackList, self).unlink()


class MailBlackListMixin(models.Model):
    """ Mixin that is inherited by all model with opt out.
        USAGE : the field '_email_field_name' must be overridden in the model that inherit the mixin
        and must contain the email field of the model.
        """
    _name = 'mail.mass_mailing.blacklist.mixin'
    _description = 'Mail Blacklist mixin'

    # field that will be overriden in the model that inherit the mixin
    # to know on which field the _compute_is_blacklisted() must depend
    _email_field_name = []

    # Creates the depends expression to work with two fields, one known and one from model that inherit the mixin.
    def _get_depends(self):
        if self._email_field_name:
            [email_field] = self._email_field_name
            return ['blacklist_id.email', email_field]
        else:
            return ['blacklist_id.email']

    # blacklist_id creates an explicit link to the blacklist model
    # in order to know which email in model that inherits the mixin is impacted by changes in blacklist model.
    # an non stored fields cannot be used as dependence
    # except if there is a search method on it (that inverse the many2one dependence)
    # so each time the blacklist is modified, the blacklist_id of the impacted records is re_computed
    # and the is_blacklist field too
    blacklist_id = fields.Many2one('mail.mass_mailing.blacklist', store=False, search="_search_blacklist_id",
                                   string='Blacklist id')

    # Note :
    # With store = False, the access to the field is not evaluated because the fields is not in DB.
    # With store = True, the access to the field can be evaluated.
    is_blacklisted = fields.Boolean(string='Blacklist', compute="_compute_is_blacklisted", store=True,
        help="If the email address is on the blacklist, the contact won't receive mass mailing anymore, from any list",
        groups="base.group_user")
    blacklist_reason = fields.Char(compute="_compute_is_blacklisted", store=True)

    @api.depends(lambda self: self._get_depends())
    def _compute_is_blacklisted(self):
        [email_field] = self._email_field_name
        blacklist = self.env['mail.mass_mailing.blacklist'].sudo().search([('email', 'in', [item[email_field] for item in self])]).read(['email', 'reason'])
        for rec in self: # Optimisation : create indexed dict sorted by email and lookup in dict to get email and reason
            email = rec[email_field]
            item = next((x for x in blacklist if email == x['email']), None)
            rec.is_blacklisted = bool(item['email']) if item else False
            rec.blacklist_reason = str(item['reason']) if item and item['reason'] else ''

    def _search_blacklist_id(self, operator, value):
        if self._email_field_name:
            [email_field] = self._email_field_name
            # implement search with domain [('blacklist_id', 'in', value)]
            assert operator == 'in' and isinstance(value, list)
            black_recs = self.env['mail.mass_mailing.blacklist'].browse(value)
            emails = black_recs.mapped('email')
            return [(email_field, 'in', emails)]
        # else:
        #     return []

    @api.multi
    def toggle_blacklist(self):
        [email_field] = self._email_field_name
        self.ensure_one()
        email = self[email_field]
        if email and re.match(EMAIL_PATTERN, email):
            blacklist = self.env["mail.mass_mailing.blacklist"]
            blacklist_rec = blacklist.sudo().search([('email', '=', email)])
            if blacklist_rec.email:
                blacklist_rec.sudo().unlink()
                return False
            else:
                blacklist.sudo().create({
                    'email': email,
                    'reason': "%s has blacklisted the recipient from %s" % (self.env['res.users'].browse(self._uid).name, self._description)
                })
                return True
        return 'not_found'
