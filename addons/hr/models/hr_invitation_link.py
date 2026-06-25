# Part of Odoo. See LICENSE file for full copyright and licensing details.
import uuid

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import email_normalize


class HrInvitationLink(models.Model):
    _name = 'hr.invitation.link'
    _description = "Employee Invitation Link"
    _order = 'create_date desc'

    def _default_access_token(self):
        return uuid.uuid4().hex

    name = fields.Char(
        string="Name", default=lambda self: _("Invitation Link"),
        help="Internal label to recognize this link.")
    access_token = fields.Char(
        string="Token", required=True, copy=False, index=True, readonly=True,
        default=_default_access_token)
    url = fields.Char(string="Invitation Link", compute='_compute_url')

    max_uses = fields.Integer(
        string="Max Uses", default=10,
        help="Maximum number of accounts that can be created through this link. "
             "Leave at 0 for an unlimited number of uses.")
    used_count = fields.Integer(string="Used", default=0, readonly=True, copy=False)
    expiration_datetime = fields.Datetime(
        string="Expires On",
        help="The link can no longer be used after this date. Leave empty for a link that never expires.")
    allowed_email_domains = fields.Text(
        string="Restrict Domain",
        help="Only users with an email matching one of these domains will be able to register. "
             "You can list multiple domains, one per line")

    company_id = fields.Many2one(
        'res.company', string="Company", required=True,
        default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    _access_token_uniq = models.Constraint(
        'unique(access_token)',
        "An invitation link with this token already exists.")
    _max_uses_positive = models.Constraint(
        'check(max_uses >= 0)',
        "The maximum number of uses cannot be negative.")

    @api.depends('access_token')
    def _compute_url(self):
        for link in self:
            base_url = link.get_base_url()
            link.url = f"{base_url}/hr/invite/{link.id}/{link.access_token}" if link.access_token else False

    def _normalize_domains(self):
        """Return the list of allowed bare domains (lower-cased, no leading '@')."""
        self.ensure_one()
        if not self.allowed_email_domains:
            return []
        raw = self.allowed_email_domains.replace(',', '\n').replace(';', '\n').split('\n')
        return [d.strip().lstrip('@').lower() for d in raw if d.strip()]

    @api.constrains('allowed_email_domains')
    def _check_allowed_email_domains(self):
        for link in self:
            for domain in link._normalize_domains():
                if '@' in domain or ' ' in domain or '.' not in domain:
                    raise ValidationError(_(
                        "%(domain)s is not a valid email domain.", domain=domain))

    def _is_email_domain_allowed(self, email):
        """Whether ``email`` may register through this link."""
        self.ensure_one()
        domains = self._normalize_domains()
        if not domains:
            return True
        normalized = email_normalize(email)
        return bool(normalized) and normalized.split('@')[-1] in domains

    def _is_valid(self):
        """Return (ok, reason) telling whether the link can still be used."""
        self.ensure_one()
        if not self.active:
            return False, _("This invitation link has been disabled.")
        if self.expiration_datetime and self.expiration_datetime < fields.Datetime.now():
            return False, _("This invitation link has expired.")
        if self.max_uses and self.used_count >= self.max_uses:
            return False, _("This invitation link has reached its maximum number of uses.")
        return True, ""

    def _consume(self):
        """Atomically register one more use, guarding against over-quota races."""
        self.ensure_one()
        link = self.sudo()
        # Re-read under a row lock so concurrent signups cannot exceed max_uses.
        self.env.cr.execute(
            "SELECT used_count, max_uses FROM hr_invitation_link WHERE id = %s FOR UPDATE",
            [link.id])
        used_count, max_uses = self.env.cr.fetchone()
        if max_uses and used_count >= max_uses:
            raise ValidationError(_("This invitation link has reached its maximum number of uses."))
        link.used_count = used_count + 1

    def action_create_link(self):
        """Footer action of the wizard: persist the link and re-open it so the
        generated URL is shown with its copy button."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.invitation.link',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': dict(self.env.context, dialog_size='medium'),
        }
