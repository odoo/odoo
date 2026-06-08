from odoo import api, fields, models
from urllib.parse import urlparse


class Website(models.CachedModel):
    _name = 'website'
    _description = "Website"
    _order = "sequence, id"

    # ir.http:_match is called by ir.http:_serve_db at a time when the
    # environment hasn't been completely initialized (i.e. before the method
    # ir.http:_authenticate is called by ir.http:_serve_ir_http), and its
    # context language hasn't been checked against activated languages yet.
    #
    # Inside ir.http:_match, the http_routing module is trying to retrieve the
    # default language via _get_default_lang, which is overridden by the
    # website module and accesses website.default_lang_id.
    #
    # Here, we cache the needed fields only to avoid prefetching any
    # translatable field, such as contact_us_link_url by website_sale, as
    # translating to an invalid language would result in an error.
    _clear_cache_name = 'default'

    @property
    def _cached_data_fields(self):
        return [
            f.name
            for f in self._fields.values()
            if f.name != 'id'
            if f.prefetch is True
            if not f.groups
        ]

    @api.ormcache(cache='default')
    def _cached_data(self):
        # method is overridden to use cache 'default' instead of 'stable'
        # hack: retrieve the original method to skip the ormcache wrapper
        return super()._cached_data.__cache__.method(self)

    name = fields.Char('Website Name', required=True)
    sequence = fields.Integer(default=10)
    user_id = fields.Many2one('res.users', string='Public User', required=True)  # TODO to rename user_id into public_user_id
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, required=True)

    domain = fields.Char('Website Domain', help='E.g. https://www.mydomain.com')
    domain_punycode = fields.Char(
        string="Punycode Domain",
        compute="_compute_domain_punycode",
        store=True,
        readonly=True)
    _domain_unique = models.Constraint(
        'unique(domain)',
        'Website Domain should be unique.',
    )

    @api.depends('domain')
    def _compute_domain_punycode(self):
        """Compute the punycode (ASCII-safe) version of the domain."""
        for website in self:
            website_domain = website.domain or ''
            hostname = urlparse(website_domain).hostname or ''
            try:
                punycode_hostname = hostname.encode('idna').decode('ascii')
                website.domain_punycode = website_domain.replace(hostname, punycode_hostname)
            except UnicodeError:
                website.domain_punycode = website_domain
