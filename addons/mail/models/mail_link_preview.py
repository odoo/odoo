import re
import typing
from typing import Self
from urllib.parse import urlparse

from dateutil.relativedelta import relativedelta
from lxml import html
from psycopg import IntegrityError

from odoo import api, fields, models, tools
from odoo.libs.debug_log import DebugLog
from odoo.tools.misc import OrderedSet

from odoo.addons.mail.tools.discuss import Store, StoreFieldsInput
from odoo.addons.mail.tools.link_preview import (
    get_link_preview_from_url,
    get_link_preview_session,
)

if typing.TYPE_CHECKING:
    from .mail_message import MailMessage
    from .mail_message_link_preview import MessageMailLinkPreview

_debug = DebugLog(__name__)


class MailLinkPreview(models.Model):
    _name = "mail.link.preview"
    _inherit = ["mixin.bus.listener"]
    _description = "Store link preview data"
    _rec_name = "source_url"

    source_url = fields.Char(
        string="URL",
        required=True,
    )
    source_url_netloc = fields.Char(
        string="URL host",
        compute="_compute_source_url_netloc",
        store=True,
        index=True,
        help="Parsed host of source_url, used for per-host throttling.",
    )
    og_type = fields.Char(string="Type")
    og_title = fields.Char(string="Title")
    og_site_name = fields.Char(string="Site name")
    og_image = fields.Char(string="Image")
    og_description = fields.Text(string="Description")
    og_mimetype = fields.Char(string="MIME type")
    image_mimetype = fields.Char(string="Image MIME type")
    create_date = fields.Datetime(index=True)
    message_link_preview_ids: MessageMailLinkPreview = fields.One2many(
        comodel_name="mail.message.link.preview",
        inverse_name="link_preview_id",
        groups="base.group_erp_manager",
    )

    _unique_source_url = models.UniqueIndex("(source_url)")

    @api.model
    def _create_from_message_and_notify(
        self, message: MailMessage, request_url: str | None = None
    ) -> None:
        urls = []
        if not tools.is_html_empty(message.body):
            urls = OrderedSet(
                html.fromstring(message.body).xpath("//a[not(@data-oe-model)]/@href")
            )
            if request_url:
                ignore_pattern = re.compile(
                    f"{re.escape(request_url)}(odoo|web|chat)(/|$|#|\\?)"
                )
                urls = list(filter(lambda url: not ignore_pattern.match(url), urls))
        requests_session = get_link_preview_session(self.env)
        message_link_previews_ok = self.env["mail.message.link.preview"]
        link_previews_values = []
        message_link_previews_values = []
        message_link_preview_by_url = {
            message_link_preview.link_preview_id.source_url: message_link_preview
            for message_link_preview in message.sudo().message_link_preview_ids
        }
        link_preview_by_url = {}
        if uncovered_urls := [
            url for url in urls if url not in message_link_preview_by_url
        ]:
            link_preview_by_url = {
                link_preview.source_url: link_preview
                for link_preview in self.env["mail.link.preview"].search(
                    [("source_url", "in", uncovered_urls)]
                )
            }
        for index, url in enumerate(urls):
            if message_link_preview := message_link_preview_by_url.get(url):
                message_link_preview.sequence = index
                message_link_previews_ok += message_link_preview
            elif link_preview := link_preview_by_url.get(url):
                message_link_previews_values.append((index, link_preview))
            elif not self._is_domain_throttled(url):
                if link_preview_values := get_link_preview_from_url(
                    url, requests_session
                ):
                    link_previews_values.append((index, link_preview_values))
            if (
                len(message_link_previews_ok)
                + len(message_link_previews_values)
                + len(link_previews_values)
                >= 5
            ):
                break
        new_link_preview_by_url = {
            link_preview.source_url: link_preview
            for link_preview in self.env[
                "mail.link.preview"
            ]._create_from_values_race_safe(
                [values for sequence, values in link_previews_values]
            )
        }
        for sequence, values in link_previews_values:
            message_link_previews_values.append(
                (sequence, new_link_preview_by_url[values["source_url"]])
            )
        _debug.pipeline(
            "link_previews",
            message=message.id,
            urls=len(urls),
            kept=len(message_link_previews_ok),
            reused=len(message_link_previews_values) - len(link_previews_values),
            fetched=len(link_previews_values),
        )
        message_link_previews_ok += self.env["mail.message.link.preview"].create(
            [
                {
                    "sequence": sequence,
                    "link_preview_id": link_preview.id,
                    "message_id": message.id,
                }
                for sequence, link_preview in message_link_previews_values
            ]
        )
        (
            message.sudo().message_link_preview_ids - message_link_previews_ok
        )._unlink_and_notify()
        Store(
            bus_channel=message._bus_channel(),
        ).add(message, "message_link_preview_ids").bus_send()

    @api.model
    def _is_link_preview_enabled(self) -> bool:
        link_preview_throttle = self.env["ir.config_parameter"]._get_int_param(
            "mail.link_preview_throttle", 99
        )
        return link_preview_throttle > 0

    @api.depends("source_url")
    def _compute_source_url_netloc(self) -> None:
        for preview in self:
            preview.source_url_netloc = urlparse(preview.source_url or "").netloc

    def _is_domain_throttled(self, url: str) -> bool:
        domain = urlparse(url).netloc
        date_interval = fields.Datetime.to_string(
            self.env.cr.now() - relativedelta(seconds=10)
        )
        call_counter = self.env["mail.link.preview"].search_count(
            [
                ("create_date", ">", date_interval),
                ("source_url_netloc", "=", domain),
            ]
        )
        link_preview_throttle = self.env["ir.config_parameter"]._get_int_param(
            "mail.link_preview_throttle", 99
        )
        if _debug.logic.enabled and call_counter > link_preview_throttle:
            _debug.logic(
                "domain_throttled",
                domain=domain,
                calls=call_counter,
                throttle=link_preview_throttle,
            )
        return call_counter > link_preview_throttle

    @api.model
    def _create_from_values_race_safe(self, values_list: list[dict]) -> Self:
        previews = self.browse()
        raced_urls = []
        for values in values_list:
            try:
                with self.env.cr.savepoint():
                    previews += self.create(values)
            except IntegrityError:
                raced_urls.append(values["source_url"])
        if raced_urls:
            _debug.logic("previews_raced", urls=len(raced_urls))
            previews += self.search([("source_url", "in", raced_urls)])
        return previews

    @api.model
    def _search_or_create_from_url(self, url: str) -> Self:
        preview = self.env["mail.link.preview"].search(
            [("source_url", "=", url)], limit=1
        )
        if not preview:
            if self._is_domain_throttled(url):
                return self.env["mail.link.preview"]
            preview_values = get_link_preview_from_url(
                url, get_link_preview_session(self.env)
            )
            if not preview_values:
                return self.env["mail.link.preview"]
            preview = self._create_from_values_race_safe([preview_values])
        return preview

    def _to_store_defaults(self, target: Store.Target) -> StoreFieldsInput:
        return [
            "image_mimetype",
            "og_description",
            "og_image",
            "og_mimetype",
            "og_site_name",
            "og_title",
            "og_type",
            "source_url",
        ]

    @api.autovacuum
    def _gc_link_previews(self) -> None:
        threshold = fields.Datetime.now() - relativedelta(weeks=2)
        stale = self.search(
            [
                ("message_link_preview_ids", "=", False),
                ("create_date", "<", threshold),
            ]
        )
        _debug.lifecycle("gc_link_previews", removed=len(stale))
        stale.unlink()
