# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo.exceptions import AccessError, UserError
from odoo.tools import SQL


class MailBlackListMixin(models.AbstractModel):
    """ Mixin that is inherited by all model with opt out. This mixin stores a normalized
    email based on primary_email field.

    A normalized email is considered as :
        - having a left part + @ + a right part (the domain can be without '.something')
        - being lower case
        - having no name before the address. Typically, having no 'Name <>'
    Ex:
        - Formatted Email : 'Name <NaMe@DoMaIn.CoM>'
        - Normalized Email : 'name@domain.com'

    The primary email field can be specified on the parent model, if it differs from the default one ('email')
    The email_normalized field can than be used on that model to search quickly on emails (by simple comparison
    and not using time consuming regex anymore).

    Using this email_normalized field, blacklist status is computed.

    Mail Thread capabilities are required for this mixin. """

    _name = 'mail.thread.blacklist'
    _inherit = ['mail.thread']
    _description = 'Mail Blacklist mixin'
    _primary_email = 'email'

    email_normalized = fields.Char(
        string='Normalized Email', compute="_compute_email_normalized", compute_sudo=True, store=True,
        help="This field is used to search on email address as the primary email field can contain more than strictly an email address.")
    # Note : is_blacklisted sould only be used for display. As the compute is not depending on the blacklist,
    # once read, it won't be re-computed again if the blacklist is modified in the same request.
    is_blacklisted = fields.Boolean(
        string='Blacklist', compute="_compute_is_blacklisted", compute_sudo=True, store=False,
        search="_search_is_blacklisted", groups="base.group_user",
        help="If the email address is on the blacklist, the contact won't receive mass mailing anymore, from any list")
    # messaging
    message_bounce = fields.Integer('Bounce', help="Counter of the number of bounced emails for this contact", default=0)

    @api.depends(lambda self: [self._primary_email])
    def _compute_email_normalized(self):
        self._assert_primary_email()
        for record in self:
            record.email_normalized = tools.email_normalize(record[self._primary_email], strict=False)

    @api.model
    def _search_is_blacklisted(self, operator, value):
        # Assumes operator is '=' or '!=' and value is True or False
        self.flush_model(['email_normalized'])
        self.env['mail.blacklist'].flush_model(['email', 'active'])
        self._assert_primary_email()
        if operator != '=':
            if operator == '!=' and isinstance(value, bool):
                value = not value
            else:
                raise NotImplementedError()

        if value:
            sql = SQL("""
                SELECT m.id
                    FROM mail_blacklist bl
                    JOIN %s m
                    ON m.email_normalized = bl.email AND bl.active
            """, SQL.identifier(self._table))
        else:
            sql = SQL("""
                SELECT m.id
                    FROM %s m
                    LEFT JOIN mail_blacklist bl
                    ON m.email_normalized = bl.email AND bl.active
                    WHERE bl.id IS NULL
            """, SQL.identifier(self._table))

        self._cr.execute(SQL("%s FETCH FIRST ROW ONLY", sql))
        res = self._cr.fetchall()
        if not res:
            return [(0, '=', 1)]
        return [('id', 'in', SQL("(%s)", sql))]

    @api.depends('email_normalized')
    def _compute_is_blacklisted(self):
        # TODO : Should remove the sudo as compute_sudo defined on methods.
        # But if user doesn't have access to mail.blacklist, doen't work without sudo().
        blacklist = set(self.env['mail.blacklist'].sudo().search([
            ('email', 'in', self.mapped('email_normalized'))]).mapped('email'))
        for record in self:
            record.is_blacklisted = record.email_normalized in blacklist

    def _assert_primary_email(self):
        if not hasattr(self, "_primary_email") or not isinstance(self._primary_email, str):
            raise UserError(_('Invalid primary email field on model %s', self._name))
        if self._primary_email not in self._fields or self._fields[self._primary_email].type != 'char':
            raise UserError(_('Invalid primary email field on model %s', self._name))

    def _message_receive_bounce(self, email, partner):
        """ Override of mail.thread generic method. Purpose is to increment the
        bounce counter of the record. """
        super(MailBlackListMixin, self)._message_receive_bounce(email, partner)
        for record in self:
            record.message_bounce = record.message_bounce + 1

    def _message_reset_bounce(self, email):
        """ Override of mail.thread generic method. Purpose is to reset the
        bounce counter of the record. """
        super(MailBlackListMixin, self)._message_reset_bounce(email)
        self.write({'message_bounce': 0})

    def mail_action_blacklist_remove(self):
        # wizard access rights currently not working as expected and allows users without access to
        # open this wizard, therefore we check to make sure they have access before the wizard opens.
        can_access = self.env['mail.blacklist'].has_access('write')
        if can_access:
            return {
                'name': _('Are you sure you want to unblacklist this Email Address?'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mail.blacklist.remove',
                'target': 'new',
            }
        else:
            raise AccessError(_("You do not have the access right to unblacklist emails. Please contact your administrator."))

    @api.model
    def _detect_loop_sender_domain(self, email_from_normalized):
        """Return the domain to be used to detect duplicated records created by alias.

        :param email_from_normalized: FROM of the incoming email, normalized
        """
        return [('email_normalized', '=', email_from_normalized)]
