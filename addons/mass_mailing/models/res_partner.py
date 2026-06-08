# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _mailing_enabled = True

    mailing_contact_id = fields.Many2one(
        'mailing.contact', compute='_compute_mailing_contact_id', string="Contact",
        groups="mass_mailing.group_mass_mailing_user")
    mailing_contact_ids = fields.One2many(
        'mailing.contact', 'partner_id', string="Contacts", groups="mass_mailing.group_mass_mailing_user")

    @api.depends('email_normalized', 'mailing_contact_ids')
    @api.depends_context('default_list_ids')
    def _compute_mailing_contact_id(self):
        """Assign the context-dependent (best) linked contact as determined by `MailingContact._get_sort_key`.

        Note: `mailing_contact_id` will be set to `False` if `default_list_ids` is provided and no linked contact
        has a `mailing.subscription` for it (opted out or not).
        This is particularly convenient to avoid creating duplicate contacts in `MailingContact._from_partners`
        if a newer contacts subscribed to the context mailing list exists but is not linked to the partner.
        """
        self.mailing_contact_id = False
        active_list_id = self.env['mailing.contact']._get_context_active_list_id()
        subscribing_contacts = self.env['mailing.subscription'].search(
            Domain('contact_id', 'in', self.mailing_contact_ids.ids) & Domain('list_id', '=', active_list_id)
        ).contact_id
        for partner in self.filtered('mailing_contact_ids'):
            partner.mailing_contact_id = partner.mailing_contact_ids.sorted(
                lambda c: c._get_sort_key(list_id=active_list_id, partner=partner))[-1]
            if active_list_id and partner.mailing_contact_id not in subscribing_contacts:
                partner.mailing_contact_id = False

    def action_open_mailing_contacts(self):
        """Open form view if a single Mailing Contact is linked, multi-record view otherwise."""
        self.ensure_one()
        if not self.mailing_contact_id:
            return None

        if len(self.mailing_contact_ids) == 1 or self.env['mailing.contact']._get_context_active_list_id():
            return self.mailing_contact_id.get_record_default_action()

        return self.env['ir.actions.actions']._for_xml_id('mass_mailing.action_view_mass_mailing_contacts') | {
            'context': {
                'default_partner_id': self.id,
            },
            'domain': [('partner_id', '=', self.id)],
            'target': 'current',
        }
