from markupsafe import Markup, escape

from odoo import _, api, fields, models

from odoo.addons.l10n_fr_pdp.utils import transport_parties as parties


class AccountMove(models.Model):
    _inherit = 'account.move'

    # The transport envelope is not in the XML and is not kept by the proxy fetch.
    # Party identifiers are parsed from the attachment instead of a stored JSON column.
    l10n_fr_pdp_transport_sender = fields.Char(
        string='Transport Sender',
        readonly=True,
        copy=False,
        help="Peppol participant that delivered this document. "
             "Taken from the transport envelope, not from the XML.",
    )
    l10n_fr_pdp_transport_receiver = fields.Char(
        string='Transport Receiver',
        readonly=True,
        copy=False,
    )
    l10n_fr_pdp_transport_party_role = fields.Selection(
        selection=[('seller', 'Seller'), ('buyer', 'Buyer')],
        string='Compared XML Party',
        compute='_compute_l10n_fr_pdp_transport_alert',
    )
    l10n_fr_pdp_transport_parties_display = fields.Char(
        string='XML Party Identifiers',
        compute='_compute_l10n_fr_pdp_transport_alert',
    )
    l10n_fr_pdp_transport_alert_level = fields.Selection(
        selection=[
            (parties.LEVEL_NONE, 'None'),
            (parties.LEVEL_WARNING, 'Warning'),
            (parties.LEVEL_CRITICAL, 'Critical'),
        ],
        string='Transport Alert',
        compute='_compute_l10n_fr_pdp_transport_alert',
    )
    l10n_fr_pdp_transport_alert_message = fields.Text(
        string='Transport Alert Message',
        compute='_compute_l10n_fr_pdp_transport_alert',
    )
    l10n_fr_pdp_transport_needs_review = fields.Boolean(
        compute='_compute_l10n_fr_pdp_transport_alert',
    )
    l10n_fr_pdp_transport_confirmed_uid = fields.Many2one(
        'res.users',
        string='Transport Alert Confirmed By',
        readonly=True,
        copy=False,
        help="User who confirmed that this document may be posted even though the transport sender "
             "does not match the party declared in the XML.",
    )
    l10n_fr_pdp_transport_confirmed_date = fields.Datetime(
        string='Transport Alert Confirmed On',
        readonly=True,
        copy=False,
    )

    @api.depends(
        'l10n_fr_pdp_transport_sender',
        'l10n_fr_pdp_transport_confirmed_uid',
        'partner_id.commercial_partner_id.l10n_fr_pdp_billing_mandate',
        'state',
        'attachment_ids',
    )
    @api.depends_context('company')
    def _compute_l10n_fr_pdp_transport_alert(self):
        trees = self.filtered('l10n_fr_pdp_transport_sender')._l10n_fr_pdp_transport_xml_trees()
        for move in self:
            sender = move.l10n_fr_pdp_transport_sender
            role = False
            tokens = []
            if sender:
                parsed = parties.parse_parties(trees.get(move.id))
                role = 'buyer' if parsed['type_code'] in parties.SELF_BILLING_TYPE_CODES else 'seller'
                tokens = parsed[role]
            mandate = False
            if sender and move.partner_id:
                mandate = move.partner_id.commercial_partner_id.with_company(move.company_id).l10n_fr_pdp_billing_mandate
            level, reason = parties.compute_alert(sender, tokens, mandate=bool(mandate))
            move.l10n_fr_pdp_transport_party_role = role
            move.l10n_fr_pdp_transport_parties_display = ', '.join(
                f'{scheme}:{value}' if scheme else value for scheme, value in tokens
            )
            move.l10n_fr_pdp_transport_alert_level = level
            move.l10n_fr_pdp_transport_alert_message = (
                move._l10n_fr_pdp_transport_message(reason, role, sender, tokens) if reason else False
            )
            move.l10n_fr_pdp_transport_needs_review = (
                level != parties.LEVEL_NONE
                and move.state == 'draft'
                and not move.l10n_fr_pdp_transport_confirmed_uid
            )

    def _l10n_fr_pdp_transport_xml_trees(self):
        """First XML tree linked to each move, including a Factur-X embedded file."""
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', 'in', self.ids),
        ])
        by_move = {}
        for attachment in attachments:
            by_move.setdefault(attachment.res_id, self.env['ir.attachment'])
            by_move[attachment.res_id] |= attachment
        trees = {}
        for move in self:
            move_attachments = by_move.get(move.id, self.env['ir.attachment'])
            trees[move.id] = next(
                (
                    file_data['xml_tree']
                    for file_data in move_attachments._unwrap_edi_attachments()
                    if file_data.get('xml_tree') is not None
                ),
                None,
            )
        return trees

    def _l10n_fr_pdp_transport_message(self, reason, role, sender, tokens):
        self.ensure_one()
        role_label = _('buyer (self-billing)') if role == 'buyer' else _('seller')
        parties_display = ', '.join(
            f'{scheme}:{value}' if scheme else value for scheme, value in tokens
        ) or '-'
        values = {'sender': sender, 'role': role_label, 'parties': parties_display}
        if reason == parties.REASON_SIREN_MISMATCH:
            return _(
                "The transport sender (%(sender)s) is not the %(role)s declared in the XML (%(parties)s). "
                "The document may have been delivered by a third party on behalf of this %(role)s.",
                **values,
            )
        if reason == parties.REASON_AMBIGUOUS:
            return _(
                "The %(role)s declared in the XML carries several SIREN (%(parties)s), "
                "the transport sender is %(sender)s. Check that the document comes from the right vendor.",
                **values,
            )
        if reason == parties.REASON_MISSING_PARTIES:
            return _(
                "The transport sender is %(sender)s but no %(role)s identifier could be read in the XML.",
                **values,
            )
        return _(
            "The transport sender (%(sender)s) cannot be compared with the %(role)s identifiers of the XML (%(parties)s).",
            **values,
        )

    def _l10n_fr_pdp_warn_transport_senders(self, transport_map):
        """Store the transport envelope of a fetch and raise the alert when it does not match the XML."""
        if not self or not transport_map:
            return
        for move in self:
            transport = transport_map.get(move.peppol_message_uuid) or {}
            if (transport.get('sender') or '').strip():
                move._l10n_fr_pdp_transport_apply(transport)

    def _l10n_fr_pdp_transport_apply(self, transport):
        self.ensure_one()
        sender = (transport.get('sender') or '').strip()
        if not sender:
            return
        self.write({
            'l10n_fr_pdp_transport_sender': sender,
            'l10n_fr_pdp_transport_receiver': (transport.get('receiver') or '').strip() or False,
        })
        if self.l10n_fr_pdp_transport_alert_level != parties.LEVEL_NONE:
            self._l10n_fr_pdp_transport_notify()

    def _l10n_fr_pdp_transport_notify(self):
        self.ensure_one()
        body = Markup('<b>%s</b> %s') % (
            _("Peppol transport alert:"),
            escape(self.l10n_fr_pdp_transport_alert_message or ''),
        )
        self.message_post(body=body, message_type='notification', subtype_xmlid='mail.mt_note')
        # 17.0 has no vendor-bill autopost hook. to_check is what _autopost_draft_entries already skips.
        self.to_check = True
        reviewer = self.company_id.l10n_fr_pdp_transport_alert_user_id
        if reviewer:
            self.activity_schedule(
                'l10n_fr_pdp.mail_activity_transport_alert',
                user_id=reviewer.id,
                note=self.l10n_fr_pdp_transport_alert_message,
            )

    def _post(self, soft=True):
        # Never post unattended a document whose transport sender is still doubtful.
        if not self.env.context.get('l10n_fr_pdp_skip_transport_check'):
            blocked = self.filtered('l10n_fr_pdp_transport_needs_review')
            if blocked:
                for move in blocked:
                    move.to_check = True
                    move.message_post(
                        body=_("Auto-post was disabled on this invoice because of a Peppol transport alert."),
                        message_type='notification',
                        subtype_xmlid='mail.mt_note',
                    )
                self = self - blocked
            if not self:
                return self.browse()
        return super()._post(soft)

    def action_post(self):
        if not self.env.context.get('l10n_fr_pdp_skip_transport_check'):
            flagged = self.filtered('l10n_fr_pdp_transport_needs_review')
            if flagged:
                others = self - flagged
                if others:
                    super(AccountMove, others).action_post()
                wizard = self.env['l10n.fr.pdp.transport.confirm'].create({'move_ids': flagged.ids})
                return wizard._get_records_action(name=_("Peppol transport alert"), target='new')
        return super().action_post()
