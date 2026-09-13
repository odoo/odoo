from datetime import UTC, datetime, timedelta

from odoo import api, fields, models
from odoo.libs.datetime import timezone
from odoo.tools import is_html_empty
from odoo.tools.date_utils import float_to_time
from odoo.tools.translate import html_translate


class EventSponsor(models.Model):
    _name = "event.sponsor"
    _description = "Event Sponsor"
    _order = "sequence, sponsor_type_id"
    _rec_name = "name"
    _inherit = [
        "mixin.mail.thread",
        "mixin.mail.activity",
        "mixin.website.published",
        "mixin.website.searchable",
    ]

    def _default_sponsor_type_id(self):
        return (
            self.env["event.sponsor.type"].search([], order="sequence desc", limit=1).id
        )

    event_id = fields.Many2one(
        comodel_name="event.event",
        index=True,
        required=True,
    )
    sponsor_type_id = fields.Many2one(
        comodel_name="event.sponsor.type",
        string="Sponsorship Level",
        default=lambda self: self._default_sponsor_type_id(),
        required=True,
        bypass_search_access=True,
    )
    url = fields.Char(
        string="Sponsor Website",
        compute="_compute_url",
        store=True,
        readonly=False,
    )
    sequence = fields.Integer()
    active = fields.Boolean(default=True)
    subtitle = fields.Char(string="Slogan")
    exhibitor_type = fields.Selection(
        selection=[
            ("sponsor", "Footer Logo Only"),
            ("exhibitor", "Exhibitor"),
            ("online", "Online Exhibitor"),
        ],
        string="Sponsor Type",
        default="sponsor",
    )
    website_description = fields.Html(
        string="Description",
        translate=html_translate,
        sanitize_overridable=True,
        sanitize_attributes=False,
        sanitize_form=True,
        compute="_compute_website_description",
        store=True,
        readonly=False,
    )
    show_on_ticket = fields.Boolean(
        string="Show on ticket",
        default=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        required=True,
        bypass_search_access=True,
    )
    partner_name = fields.Char(
        related="partner_id.name",
        string="Name",
    )
    partner_email = fields.Char(
        related="partner_id.email",
        string="Email",
    )
    partner_phone_ids = fields.Many2many(
        related="partner_id.phone_ids",
        string="Phone",
    )
    name = fields.Char(
        string="Sponsor Name",
        compute="_compute_name",
        store=True,
        readonly=False,
    )
    email = fields.Char(
        string="Sponsor Email",
        compute="_compute_email",
        store=True,
        readonly=False,
    )
    phone_ids = fields.Many2many(
        comodel_name="phone.number",
        relation="event_sponsor_phone_number_rel",
        column1="sponsor_id",
        column2="phone_number_id",
        string="Sponsor Phone",
        compute="_compute_phone_ids",
        store=True,
        readonly=False,
    )
    image_512 = fields.Image(
        string="Logo",
        max_width=512,
        max_height=512,
        compute="_compute_image_512",
        store=True,
        readonly=False,
    )
    image_256 = fields.Image(
        related="image_512",
        string="Image 256",
        max_width=256,
        max_height=256,
        store=False,
    )
    image_128 = fields.Image(
        related="image_512",
        string="Image 128",
        max_width=128,
        max_height=128,
        store=False,
    )
    website_image_url = fields.Char(
        string="Image URL",
        compute="_compute_website_image_url",
        compute_sudo=True,
        store=False,
    )
    hour_from = fields.Float(
        string="Opening hour",
        default=8.0,
    )
    hour_to = fields.Float(
        string="End hour",
        default=18.0,
    )
    event_date_tz = fields.Selection(
        related="event_id.date_tz",
        string="Timezone",
        readonly=True,
    )
    is_in_opening_hours = fields.Boolean(
        string="Within opening hours",
        compute="_compute_is_in_opening_hours",
    )
    country_id = fields.Many2one(
        comodel_name="res.country",
        related="partner_id.country_id",
        string="Country",
        readonly=True,
    )
    country_flag_url = fields.Char(
        string="Country Flag",
        compute="_compute_country_flag_url",
        compute_sudo=True,
    )

    @api.depends("partner_id")
    def _compute_url(self):
        for sponsor in self:
            if sponsor.partner_id.website or not sponsor.url:
                sponsor.url = sponsor.partner_id.website

    @api.depends("partner_id")
    def _compute_name(self):
        self._sync_with_partner("name")

    @api.depends("partner_id")
    def _compute_email(self):
        self._sync_with_partner("email")

    @api.depends("partner_id")
    def _compute_phone_ids(self):
        for sponsor in self:
            if not sponsor.phone_ids:
                sponsor.phone_ids = sponsor.partner_id.phone_ids._primary()

    @api.depends("partner_id")
    def _compute_image_512(self):
        self._sync_with_partner("image_512")

    @api.depends("image_512", "partner_id.image_256")
    def _compute_website_image_url(self):
        for sponsor in self:
            if sponsor.image_512:
                sponsor.website_image_url = self.env["website"].image_url(
                    sponsor, "image_256", size=256
                )
            elif sponsor.partner_id.image_256:
                sponsor.website_image_url = self.env["website"].image_url(
                    sponsor.partner_id, "image_256", size=256
                )
            else:
                sponsor.website_image_url = (
                    "/website_event_exhibitor/static/src/img/event_sponsor_default.svg"
                )

    def _sync_with_partner(self, fname):
        for sponsor in self:
            if not sponsor[fname]:
                sponsor[fname] = sponsor.partner_id[fname]

    @api.depends("partner_id")
    def _compute_website_description(self):
        for sponsor in self:
            if is_html_empty(sponsor.website_description):
                sponsor.website_description = sponsor.partner_id.website_description

    @api.depends(
        "event_id.is_ongoing",
        "hour_from",
        "hour_to",
        "event_id.date_begin",
        "event_id.date_end",
    )
    def _compute_is_in_opening_hours(self):
        for sponsor in self:
            if not sponsor.event_id.is_ongoing:
                sponsor.is_in_opening_hours = False
            elif sponsor.hour_from is False or sponsor.hour_to is False:
                sponsor.is_in_opening_hours = True
            else:
                event_tz = timezone(sponsor.event_id.date_tz)
                dt_begin = sponsor.event_id.date_begin.astimezone(event_tz)
                dt_end = sponsor.event_id.date_end.astimezone(event_tz)
                now_utc = (
                    fields.Datetime.now().replace(microsecond=0).replace(tzinfo=UTC)
                )
                now_tz = now_utc.astimezone(event_tz)

                opening_from_tz = datetime.combine(
                    now_tz.date(), float_to_time(sponsor.hour_from)
                ).replace(tzinfo=event_tz)
                opening_to_tz = datetime.combine(
                    now_tz.date(), float_to_time(sponsor.hour_to)
                ).replace(tzinfo=event_tz)
                if sponsor.hour_to == 0:
                    opening_to_tz += timedelta(days=1)

                opening_from = max([dt_begin, opening_from_tz])
                opening_to = min([dt_end, opening_to_tz])

                sponsor.is_in_opening_hours = opening_from <= now_tz < opening_to

    @api.depends("partner_id.country_id.image_url")
    def _compute_country_flag_url(self):
        for sponsor in self:
            if sponsor.partner_id.country_id:
                sponsor.country_flag_url = sponsor.partner_id.country_id.image_url
            else:
                sponsor.country_flag_url = False

    @api.depends("name", "event_id.name")
    def _compute_website_url(self):
        super()._compute_website_url()
        for sponsor in self:
            if sponsor.id:
                sponsor.website_url = f"/event/{self.env['ir.http']._slug(sponsor.event_id)}/exhibitor/{self.env['ir.http']._slug(sponsor)}"

    @api.depends("event_id.website_id.domain")
    def _compute_website_absolute_url(self):
        super()._compute_website_absolute_url()

    @api.model
    def _search_get_detail(self, website, order, options):
        event_id = self.env["ir.http"]._unslug(options["event"])[1]
        mapping = {
            "name": {"name": "name", "type": "text", "match": True},
            "website_url": {"name": "website_url", "type": "text", "truncate": False},
            "description": {
                "name": "website_description",
                "type": "text",
                "truncate": True,
                "html": True,
            },
        }
        return {
            "model": "event.sponsor",
            "base_domain": [
                [("event_id", "=", event_id), ("exhibitor_type", "!=", "sponsor")]
            ],
            "search_fields": ["name", "website_description"],
            "fetch_fields": ["name", "website_url", "website_description"],
            "mapping": mapping,
            "icon": "fa-black-tie",
            "order": order,
        }

    def get_backend_menu_id(self):
        return self.env.ref("event.event_main_menu").id

    def get_base_url(self):
        return self.event_id.get_base_url()
