# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MassMailingList(models.Model):
    """Model of a contact list. """
    _name = 'mailing.list'
    _order = 'name'
    _description = 'Mailing List'

    name = fields.Char(string='Mailing List', required=True)
    active = fields.Boolean(default=True)
    contact_ids = fields.Many2many(
        'mailing.contact', 'mailing_contact_list_rel', 'list_id', 'contact_id',
        string='Contact Lists')

    mailing_list_ids = fields.Many2many('mailing.mailing', 'mail_mass_mailing_list_rel', string='Mailing Lists')
    contact_ids_valid_email = fields.Many2many(
        'mailing.contact', 'mailing_contact_list_rel', 'list_id', 'contact_id',
        compute='_compute_statistic', string='Valid Email'
    )
    contact_ids_valid = fields.Many2many(
        'mailing.contact', 'mailing_contact_list_rel', 'list_id', 'contact_id',
        compute='_compute_statistic', string='Valid Contact'
    )
    contact_ids_message_bounce = fields.Many2many(
        'mailing.contact', 'mailing_contact_list_rel', 'list_id', 'contact_id',
        compute='_compute_statistic', string='Message Bounced'
    )
    contact_ids_opt_out = fields.Many2many(
        'mailing.contact', 'mailing_contact_list_rel', 'list_id', 'contact_id',
        compute='_compute_statistic', string='Opt Out'
    )
    contact_ids_blacklisted = fields.Many2many(
        'mailing.contact', 'mailing_contact_list_rel', 'list_id', 'contact_id',
        compute='_compute_statistic', string='Blacklisted Email'
    )

    contact_count = fields.Integer(compute='_compute_statistic', string='Total Contacts')
    contact_valid_count = fields.Integer(compute='_compute_statistic', string='Total Valid Contacts')
    contact_valid_email_count = fields.Integer(compute='_compute_statistic', string='Valid Email Contacts')
    mailing_list_count = fields.Integer(compute='_compute_statistic', string='Valid Contacts')

    contact_message_bounce_percentage = fields.Float(
        compute='_compute_statistic',
        string='Number of email that have at least one bounced message'
    )

    contact_blacklist_percentage = fields.Float(compute='_compute_statistic', string='Percentage black listed contact')
    contact_opt_out_percentage = fields.Float(compute='_compute_statistic', string='Percentage opt out contact')
    contact_message_bounce_percentage_str = fields.Char(compute='_compute_statistic')
    contact_blacklist_percentage_str = fields.Char(compute='_compute_statistic')
    contact_opt_out_percentage_str = fields.Char(compute='_compute_statistic')

    subscription_ids = fields.One2many(
        'mailing.contact.subscription', 'list_id', string='Subscription Information'
    )

    is_public = fields.Boolean(
        default=True,
        help="The mailing list can be accessible by recipient in the unsubscription"
        " page to allows him to update his subscription preferences."
    )


    @api.depends('contact_ids')
    def _compute_statistic(self):
        for mailing_list in self:
            contact_ids = mailing_list.contact_ids.with_context({'default_list_ids': [mailing_list.id]})
            mailing_list.contact_ids_opt_out = contact_ids.filtered('opt_out')
            mailing_list.contact_ids_blacklisted = contact_ids.filtered('is_blacklisted')
            mailing_list.contact_ids_message_bounce = contact_ids.filtered('message_bounce')
            mailing_list.contact_ids_valid_email = contact_ids.filtered(
                lambda contact: contact.email and not contact.is_blacklisted and not contact.opt_out
            )
            mailing_list.contact_ids_valid = mailing_list.contact_ids_valid_email

            mailing_list.contact_count = len(contact_ids)
            mailing_list.contact_valid_email_count = len(mailing_list.contact_ids_valid_email)
            mailing_list.contact_valid_count = len(mailing_list.contact_ids_valid)
            mailing_list.mailing_list_count = len(mailing_list.mailing_list_ids)

            mailing_list.contact_message_bounce_percentage = fields.float_round(
                len(mailing_list.contact_ids_message_bounce) / mailing_list.contact_count * 100, 2
            ) if mailing_list.contact_count > 0 else 0
            mailing_list.contact_blacklist_percentage = fields.float_round(
                len(mailing_list.contact_ids_blacklisted) / mailing_list.contact_count * 100, 2
            ) if mailing_list.contact_count > 0 else 0
            mailing_list.contact_opt_out_percentage = fields.float_round(
                len(mailing_list.contact_ids_opt_out) / mailing_list.contact_count * 100, 2
            ) if mailing_list.contact_count > 0 else 0

            mailing_list.contact_message_bounce_percentage_str = str(mailing_list.contact_message_bounce_percentage) + '%'
            mailing_list.contact_opt_out_percentage_str = str(mailing_list.contact_opt_out_percentage) + '%'
            mailing_list.contact_blacklist_percentage_str = str(mailing_list.contact_blacklist_percentage) + '%'


    def write(self, vals):
        # Prevent archiving used mailing list
        if 'active' in vals and not vals.get('active'):
            mass_mailings = self.env['mailing.mailing'].search_count([
                ('state', '!=', 'done'),
                ('contact_list_ids', 'in', self.ids),
            ])

            if mass_mailings > 0:
                raise UserError(_("At least one of the mailing list you are trying to archive is used in an ongoing mailing campaign."))

        return super(MassMailingList, self).write(vals)

    def name_get(self):
        return [(list.id, "%s (%s)" % (list.name, list.contact_valid_email_count)) for list in self]


    def action_view_full_contacts(self):
        action = self.env.ref('mass_mailing.action_view_mass_mailing_contacts').read()[0]
        action['domain'] = [('list_ids', 'in', self.ids)]
        action['context'] = dict(self.env.context, default_list_ids=self.ids)
        return action

    def action_view_valid_email_contacts(self):
        action = self.env.ref('mass_mailing.action_view_mass_mailing_contacts').read()[0]
        action['domain'] = [('list_ids', 'in', self.ids)]
        action['context'] = dict(
            self.env.context,
            default_list_ids=self.ids,
            search_default_filter_valid_email=1
        )
        return action

    def action_view_valid_contacts(self):
        return self.action_view_valid_email_contacts()

    def action_view_message_bounce_contacts(self):
        action = self.env.ref('mass_mailing.action_view_mass_mailing_contacts').read()[0]
        action['domain'] = [('list_ids', 'in', self.ids)]
        action['context'] = dict(
            self.env.context,
            default_list_ids=self.ids,
            search_default_filter_bounced=1,
        )
        return action

    def action_view_blacklisted_contacts(self):
        action = self.env.ref('mass_mailing.action_view_mass_mailing_contacts').read()[0]
        action['domain'] = [('list_ids', 'in', self.ids)]
        action['context'] = dict(
            self.env.context,
            default_list_ids=self.ids,
            search_default_filter_blacklisted=1
        )
        return action

    def action_view_opt_out_contacts(self):
        action = self.env.ref('mass_mailing.action_view_mass_mailing_contacts').read()[0]
        action['domain'] = [('list_ids', 'in', self.ids)]
        action['context'] = dict(
            self.env.context,
            default_list_ids=self.ids,
            search_default_filter_opt_out=1
        )
        return action

    def action_view_mailing(self):
        action = self.env.ref('mass_mailing.mailing_mailing_action_mail').read()[0]
        action['domain'] = [('id', 'in', self.mailing_list_ids.ids)]
        context = dict(self.env.context)
        action['context'] = context
        return action

    def action_merge(self, src_lists, archive):
        """
            Insert all the contact from the mailing lists 'src_lists' to the
            mailing list in 'self'. Possibility to archive the mailing lists
            'src_lists' after the merge except the destination mailing list 'self'.
        """
        # Explation of the SQL query with an example. There are the following lists
        # A (id=4): yti@odoo.com; yti@example.com
        # B (id=5): yti@odoo.com; yti@openerp.com
        # C (id=6): nothing
        # To merge the mailing lists A and B into C, we build the view st that looks
        # like this with our example:
        #
        #  contact_id |           email           | row_number |  list_id |
        # ------------+---------------------------+------------------------
        #           4 | yti@odoo.com              |          1 |        4 |
        #           6 | yti@odoo.com              |          2 |        5 |
        #           5 | yti@example.com           |          1 |        4 |
        #           7 | yti@openerp.com           |          1 |        5 |
        #
        # The row_column is kind of an occurence counter for the email address.
        # Then we create the Many2many relation between the destination list and the contacts
        # while avoiding to insert an existing email address (if the destination is in the source
        # for example)
        self.ensure_one()
        # Put destination is sources lists if not already the case
        src_lists |= self
        self.env['mailing.contact'].flush(['email', 'email_normalized'])
        self.env['mailing.contact.subscription'].flush(['contact_id', 'opt_out', 'list_id'])
        self.env.cr.execute("""
            INSERT INTO mailing_contact_list_rel (contact_id, list_id)
            SELECT st.contact_id AS contact_id, %s AS list_id
            FROM
                (
                SELECT
                    contact.id AS contact_id,
                    contact.email AS email,
                    list.id AS list_id,
                    row_number() OVER (PARTITION BY email ORDER BY email) AS rn
                FROM
                    mailing_contact contact,
                    mailing_contact_list_rel contact_list_rel,
                    mailing_list list
                WHERE contact.id=contact_list_rel.contact_id
                AND COALESCE(contact_list_rel.opt_out,FALSE) = FALSE
                AND contact.email_normalized NOT IN (select email from mail_blacklist where active = TRUE)
                AND list.id=contact_list_rel.list_id
                AND list.id IN %s
                AND NOT EXISTS
                    (
                    SELECT 1
                    FROM
                        mailing_contact contact2,
                        mailing_contact_list_rel contact_list_rel2
                    WHERE contact2.email = contact.email
                    AND contact_list_rel2.contact_id = contact2.id
                    AND contact_list_rel2.list_id = %s
                    )
                ) st
            WHERE st.rn = 1;""", (self.id, tuple(src_lists.ids), self.id))
        self.flush()
        self.invalidate_cache()
        if archive:
            (src_lists - self).action_archive()

    def close_dialog(self):
        return {'type': 'ir.actions.act_window_close'}
