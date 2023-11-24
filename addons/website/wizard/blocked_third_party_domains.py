from urllib3.util import parse_url
from urllib3.exceptions import LocationParseError

from odoo import fields, models, _
from odoo.exceptions import ValidationError


class BlockedThirdPartyDomains(models.TransientModel):
    _name = "website.custom_blocked_third_party_domains"
    _description = "User list of blocked 3rd-party domains"

    content = fields.Text(default=lambda s: s.env['website'].get_current_website().custom_blocked_third_party_domains)

    def action_save(self):
        domains = set()
        if self.content:
            for domain in self.content.split('\n'):
                try:
                    # Remove protocol, path and query + check that domain is
                    # valid.
                    domain = parse_url(domain.strip().lower()).host
                except LocationParseError:
                    raise ValidationError(_("The following domain is not valid:") + '\n' + domain)
                if domain:
                    domains.add(domain)

        self.env['website'].get_current_website().custom_blocked_third_party_domains = '\n'.join(domains)
        return {'type': 'ir.actions.act_window_close'}
