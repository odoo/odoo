import hashlib
import logging
import secrets
import string
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.http import request
from odoo.tools.mail import normalize_url

from odoo.addons.mail.tools import link_preview

_logger = logging.getLogger(__name__)

LINK_TRACKER_UNIQUE_FIELDS = ("url", "campaign_id", "medium_id", "source_id", "label")

#: A short code is handed to everyone who receives a mailing and is resolved
#: through a public, unthrottled route, so a guessable one discloses its target.
#: Three characters is 62**3, which a single-threaded client walks in under an
#: hour; eight is 2.2e14. Codes already issued keep working -- the column is not
#: fixed-width and only newly generated codes get the longer form.
LINK_TRACKER_MIN_CODE_LENGTH = 8
LINK_TRACKER_CODE_ALPHABET = string.ascii_letters + string.digits

#: Read on every redirect, so it is worth not paying for the whole record.
LINK_TRACKER_CLICK_ROUTE_FIELDS = ("ip", "country_id", "link_id")


class LinkTracker(models.Model):
    """Wrap any URL into a short URL whose clicks are counted and which is
    linked to UTMs, allowing to analyze marketing actions. Also used by
    mass_mailing, which converts every link of an html body into such a
    tracked short link."""

    _name = "link.tracker"
    _rec_name = "short_url"
    _description = "Link Tracker"
    # `count` alone is not a total order: ties would paginate nondeterministically
    # and make "which duplicate did the constraint name?" depend on the plan.
    _order = "count DESC, id DESC"
    _inherit = ["mixin.utm"]

    # URL info
    url = fields.Char(
        string="Target URL",
        required=True,
    )
    absolute_url = fields.Char(
        string="Absolute URL",
        compute="_compute_absolute_url",
    )
    short_url = fields.Char(
        string="Tracked URL",
        compute="_compute_short_url",
    )
    redirected_url = fields.Char(
        string="Redirected URL",
        compute="_compute_redirected_url",
    )
    short_url_host = fields.Char(
        string="Host of the short URL",
        compute="_compute_short_url_host",
    )
    title = fields.Char(string="Page Title")
    label = fields.Char(string="Button label")
    # Tracking
    link_code_ids = fields.One2many(
        comodel_name="link.tracker.code",
        inverse_name="link_id",
        string="Codes",
    )
    code = fields.Char(
        string="Short URL code",
        compute="_compute_code",
        inverse="_inverse_code",
        readonly=False,
    )
    link_click_ids = fields.One2many(
        comodel_name="link.tracker.click",
        inverse_name="link_id",
        string="Clicks",
    )
    count = fields.Integer(
        string="Number of Clicks",
        compute="_compute_count",
        store=True,
    )
    # The five unique fields, digested. Indexing the tuple itself is not an
    # option: `url` and `label` are unbounded, and a btree entry is capped at
    # ~2704 bytes. The digest is fixed-width, so one indexed `IN` answers what
    # used to be an N-way OR over an unindexed column -- see `_unique_key_domain`.
    key_hash = fields.Char(
        string="Unique key digest",
        compute="_compute_key_hash",
        store=True,
        index="btree",
        copy=False,
    )
    # UTMs - enforcing the fact that we want to 'set null' when relation is unlinked
    campaign_id = fields.Many2one(ondelete="set null")
    medium_id = fields.Many2one(ondelete="set null")
    source_id = fields.Many2one(ondelete="set null")

    # ------------------------------------------------------------
    # UNIQUE KEY
    # ------------------------------------------------------------

    @api.model
    def _unique_key_from_values(self, values):
        """Return the canonical unique key of ``values``.

        ``values`` is either a vals dict or a ``link.tracker`` record. The whole
        point is that there is exactly one spelling of this tuple: ``label``
        carries both ``''`` and ``NULL`` in the wild (see ``_normalize_vals``),
        and every consumer used to re-implement that carve-out.
        """
        if isinstance(values, models.BaseModel):
            values.check_singleton()
            return (
                values.url or "",
                values.campaign_id.id or False,
                values.medium_id.id or False,
                values.source_id.id or False,
                values.label or False,
            )
        return (
            values.get("url") or "",
            values.get("campaign_id") or False,
            values.get("medium_id") or False,
            values.get("source_id") or False,
            values.get("label") or False,
        )

    @api.model
    def _unique_key_digest(self, key):
        return hashlib.sha256(
            "\x00".join(str(part) for part in key).encode()
        ).hexdigest()

    @api.depends(*LINK_TRACKER_UNIQUE_FIELDS)
    def _compute_key_hash(self):
        for tracker in self:
            tracker.key_hash = self._unique_key_digest(
                self._unique_key_from_values(tracker)
            )

    @api.model
    def _unique_key_domain(self, keys):
        """Domain matching every tracker whose unique key is one of ``keys``.

        One indexed ``IN`` over ``key_hash``. A digest collision would only widen
        the result set, and callers re-derive the real key from each record, so
        the answer stays exact.
        """
        if not keys:
            return Domain.FALSE
        return Domain("key_hash", "in", [self._unique_key_digest(key) for key in keys])

    # ------------------------------------------------------------
    # COMPUTE
    # ------------------------------------------------------------

    @api.depends("url")
    def _compute_absolute_url(self):
        base_url = self.env["link.tracker"].get_base_url()
        for tracker in self:
            url = urlsplit(tracker.url)
            if url.scheme:
                tracker.absolute_url = tracker.url
                continue
            try:
                tracker.absolute_url = tools.urls.urljoin(base_url, urlunsplit(url))
            except ValueError as err:
                # A schemeless url is legitimate here — it is resolved against the
                # base url, which is what this branch is for — but urljoin refuses a
                # foreign host and any dot segment, and `write` does not normalise.
                # Report it the way `_compute_short_url` reports its own join
                # failure, rather than letting a bare ValueError out of a compute.
                raise UserError(
                    self.env._(
                        "“%s” is not a valid link.",
                        tracker.url,
                    )
                ) from err

    @api.depends("link_click_ids.link_id")
    def _compute_count(self):
        clicks_data = self.env["link.tracker.click"]._read_group(
            [("link_id", "in", self.ids)],
            ["link_id"],
            ["__count"],
        )
        mapped_data = {link.id: count for link, count in clicks_data}
        for tracker in self:
            tracker.count = mapped_data.get(tracker.id, 0)

    @api.depends("code", "short_url_host")
    def _compute_short_url(self):
        for tracker in self:
            try:
                tracker.short_url = tools.urls.urljoin(
                    tracker.short_url_host or "", tracker.code or ""
                )
            except ValueError as err:
                raise UserError(
                    self.env._("Please enter valid short URL code.")
                ) from err

    def _compute_short_url_host(self):
        base_url = self.env["link.tracker"].get_base_url()
        for tracker in self:
            tracker.short_url_host = base_url + "/r/"

    @api.depends("link_code_ids.code")
    def _compute_code(self):
        """The most recently issued code of each tracker, in one query.

        The dependency is what makes this correct: without it the ORM caches the
        value for the whole transaction, so renaming a code -- or adding a second
        one, which is what ``/website_links/add_code`` does -- left every reader
        of ``code``, ``short_url`` and therefore ``display_name`` on the old value.
        """
        Code = self.env["link.tracker.code"]
        latest_ids = {
            link.id: code_id
            for link, code_id in Code._read_group(
                [("link_id", "in", self.ids)],
                ["link_id"],
                ["id:max"],
            )
        }
        codes = {code.id: code.code for code in Code.browse(latest_ids.values())}
        for tracker in self:
            tracker.code = codes.get(latest_ids.get(tracker.id), False)

    def _inverse_code(self):
        """Rename the tracker's latest code, or issue one if it has none.

        Batched, and without ``check_singleton``: an inverse is handed the whole
        recordset, and this one used to raise a bare ValueError on any
        multi-record write.
        """
        Code = self.env["link.tracker.code"].sudo()
        trackers = self.filtered("code")
        if not trackers:
            return
        latest_ids = {
            link.id: code_id
            for link, code_id in Code._read_group(
                [("link_id", "in", trackers.ids)],
                ["link_id"],
                ["id:max"],
            )
        }
        to_create = []
        for tracker in trackers:
            code_id = latest_ids.get(tracker.id)
            if code_id:
                Code.browse(code_id).code = tracker.code
            else:
                to_create.append({"code": tracker.code, "link_id": tracker.id})
        if to_create:
            Code.create(to_create)

    @api.depends(
        "url",
        "campaign_id",
        "campaign_id.name",
        "medium_id",
        "medium_id.name",
        "source_id",
        "source_id.name",
    )
    def _compute_redirected_url(self):
        """Compute the URL to which we will redirect the user.

        UTM values are added as GET parameters; when the system parameter
        `link_tracker.no_external_tracking` is set, only for URLs pointing to
        the local website (base URL).
        """
        no_external_tracking = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("link_tracker.no_external_tracking")
        )
        base_domain = urlsplit(self.env["link.tracker"].get_base_url()).netloc
        tracking_fields = self.env["mixin.utm"].tracking_fields()

        for tracker in self:
            parsed = urlsplit(tracker.url)
            if no_external_tracking and parsed.netloc and parsed.netloc != base_domain:
                tracker.redirected_url = urlunsplit(parsed)
                continue

            query = dict(parse_qsl(parsed.query))
            for key, field_name, _cook in tracking_fields:
                field = self._fields[field_name]
                attr = tracker[field_name]
                if field.type == "many2one":
                    attr = attr.name
                if attr:
                    query[key] = attr

            query = urlencode(query)
            # '...' is detected as malicious by some nginx
            # configurations, encoding it solves the issue
            query = query.replace("...", "%2E%2E%2E")
            tracker.redirected_url = urlunsplit(parsed._replace(query=query))

    @api.model
    def _get_title_from_url(self, url):
        preview = link_preview.get_link_preview_from_url(
            url, link_preview.get_link_preview_session(self.env)
        )
        if preview and preview.get("og_title"):
            return preview["og_title"]
        return url

    # ------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------

    @api.model
    def _normalize_vals(self, vals):
        """Bring one vals dict to the canonical shape the unique key assumes.

        ``label`` reaches the column as both ``''`` and ``NULL`` otherwise, which
        is why the unique key needed a carve-out at every call site.
        """
        if "label" in vals and not vals["label"]:
            vals["label"] = False
        if "url" in vals:
            url = vals["url"]
            if url.startswith(("?", "#")):
                raise UserError(
                    _(
                        "“%s” is not a valid link, links cannot redirect to the current page.",
                        url,
                    )
                )
            vals["url"] = normalize_url(url)
        return vals

    def _check_url_is_not_a_short_url(self, vals_list):
        """Refuse a target that is one of our own short URLs.

        ``test_no_loop`` is named for this hazard but only guarded ``?`` and
        ``#``. A tracker pointed at its own ``/r/<code>`` 301s to itself, and
        because the click is recorded before the redirect resolves, one browser
        page-load records as many clicks as the browser's redirect limit.
        """
        short_prefix = self.env["link.tracker"].get_base_url() + "/r/"
        for vals in vals_list:
            url = vals.get("url")
            if not url:
                continue
            absolute = (
                url
                if urlsplit(url).scheme
                else tools.urls.urljoin(self.env["link.tracker"].get_base_url(), url)
            )
            if absolute.startswith(short_prefix):
                raise UserError(
                    _(
                        "“%s” is not a valid link, it already is a tracked short link.",
                        url,
                    )
                )

    def _check_unicity_of_keys(self, keys, exclude=None):
        """Raise if ``keys`` collide with each other or with existing trackers.

        Replaces the table scan the old ``@api.constrains`` ran: the lookup is a
        single indexed ``IN`` over ``key_hash`` rather than an N-way OR over an
        unindexed ``url``.
        """
        seen, duplicates = set(), []
        for key in keys:
            if key in seen:
                duplicates.append(key)
            seen.add(key)

        domain = self._unique_key_domain(list(seen))
        if exclude:
            domain &= Domain("id", "not in", exclude.ids)
        for tracker in self.sudo().search(domain):
            key = self._unique_key_from_values(tracker)
            if key in seen:
                duplicates.append(key)

        if duplicates:
            names = {}
            for model_name in ("utm.campaign", "utm.medium", "utm.source"):
                ids = {key[i] for key in duplicates for i in (1, 2, 3)}
                names.update(
                    {
                        record.id: record.name
                        for record in self.env[model_name]
                        .sudo()
                        .browse([i for i in ids if i])
                        .exists()
                    }
                )
            error_lines = "\n- ".join(
                str(
                    (
                        key[0],
                        names.get(key[1]),
                        names.get(key[2]),
                        names.get(key[3]),
                        key[4] or '""',
                    )
                )
                for key in duplicates
            )
            raise UserError(
                _(
                    "Combinations of Link Tracker values (URL, campaign, medium, source, and label) must be unique.\n"
                    "The following combinations are already used: \n- %(error_lines)s",
                    error_lines=error_lines,
                )
            )

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._normalize_vals(vals.copy()) for vals in vals_list]
        for vals in vals_list:
            if "url" not in vals:
                raise UserError(
                    _("Creating a Link Tracker without URL is not possible")
                )
        self._check_url_is_not_a_short_url(vals_list)

        # Taken out before `super`: `code` is a non-stored inverse field, and the
        # inverse runs while the tracker still has no `link.tracker.code` row --
        # it used to find nothing, return silently, and let `create` overwrite the
        # requested code with a generated one, leaving the record reporting a
        # short URL that resolved to nothing.
        requested_codes = [vals.pop("code", False) for vals in vals_list]

        for vals in vals_list:
            if not vals.get("title"):
                # Display-only, and `link_preview` fetches it over the network with
                # a 10s deadline per link. That does not belong in a transaction on
                # the mailing send path; `_cron_update_titles` backfills it, and a
                # caller that needs it now asks for it.
                vals["title"] = (
                    self._get_title_from_url(vals["url"])
                    if self.env.context.get("link_tracker_fetch_title")
                    else vals["url"]
                )

            # Prevent the UTMs from being set by the values of UTM cookies
            for __, fname, __ in self.env["mixin.utm"].tracking_fields():
                if fname not in vals:
                    vals[fname] = False

        self._check_unicity_of_keys(
            [self._unique_key_from_values(vals) for vals in vals_list]
        )
        links = super().create(vals_list)

        Code = self.env["link.tracker.code"].sudo()
        generated = iter(
            Code._get_random_code_strings(
                sum(1 for code in requested_codes if not code)
            )
        )
        Code.create(
            [
                {
                    "code": requested or next(generated),
                    "link_id": link.id,
                }
                for link, requested in zip(links, requested_codes, strict=True)
            ]
        )

        return links

    def write(self, vals):
        vals = self._normalize_vals(dict(vals))
        if vals.keys() & set(LINK_TRACKER_UNIQUE_FIELDS):
            if "url" in vals:
                self._check_url_is_not_a_short_url([vals])
            keys = []
            for tracker in self:
                merged = {
                    fname: (
                        vals[fname]
                        if fname in vals
                        else (
                            tracker[fname].id
                            if self._fields[fname].type == "many2one"
                            else tracker[fname]
                        )
                    )
                    for fname in LINK_TRACKER_UNIQUE_FIELDS
                }
                keys.append(self._unique_key_from_values(merged))
            self._check_unicity_of_keys(keys, exclude=self)
        return super().write(vals)

    # ------------------------------------------------------------
    # API
    # ------------------------------------------------------------

    @api.model
    def search_or_create(self, vals_list):
        """Get existing or newly created records matching vals_list items in preserved order supporting duplicates."""
        if not isinstance(vals_list, list):
            _logger.warning(
                "Deprecated usage of LinkTracker.search_or_create which now expects a list of dictionaries as input."
            )
            vals_list = [vals_list]

        for vals in vals_list:
            if "url" not in vals:
                raise UserError(
                    _("Creating a Link Tracker without URL is not possible")
                )
            self._normalize_vals(vals)
            # fill vals so `_unique_key_from_values` sees the defaults a create would apply
            self._add_missing_default_values(vals)
            vals.update(
                {key: False for key in LINK_TRACKER_UNIQUE_FIELDS if not vals.get(key)}
            )

        keys = [self._unique_key_from_values(vals) for vals in vals_list]
        unique_keys = set(keys)
        found_trackers = self.search(self._unique_key_domain(list(unique_keys)))
        key_to_trackers_map = {
            key: tracker
            for tracker in found_trackers
            if (key := self._unique_key_from_values(tracker)) in unique_keys
        }

        if len(unique_keys) != len(key_to_trackers_map):
            # Create trackers for values with unique keys not found
            seen_keys = set(key_to_trackers_map)
            new_trackers = self.create(
                [
                    vals
                    for vals, key in zip(vals_list, keys, strict=True)
                    if key not in seen_keys and not seen_keys.add(key)
                ]
            )
            key_to_trackers_map.update(
                (self._unique_key_from_values(tracker), tracker)
                for tracker in new_trackers
            )

        # Build final recordset following input order
        return self.browse([key_to_trackers_map[key].id for key in keys])

    @api.model
    def _resolve_and_track(self, code, **route_values):
        """Resolve a short code to its redirect target, recording the click.

        The single entry point every ``/r/`` route shares. It exists because the
        four controllers that used to spell this out drifted: two kept the
        ``is_a_bot`` guard and two lost it -- including the ``/r/<code>/m/<trace>``
        route that every mass-mailing link points at -- and all four resolved the
        same code twice, once to record the click and once to read the target.
        """
        tracker_code = (
            self.env["link.tracker.code"].sudo().search([("code", "=", code)], limit=1)
        )
        if not tracker_code:
            return None
        if not self._click_is_from_a_bot():
            self.env["link.tracker.click"].sudo().add_click(
                code, tracker_code=tracker_code, **route_values
            )
        return tracker_code.link_id.redirected_url

    @api.model
    def _click_is_from_a_bot(self):
        """Whether the current request looks like a crawler or link previewer.

        False outside an HTTP request: demo data and tests call ``add_click``
        directly and there is no user agent to read.
        """
        if not request:
            return False
        return self.env["ir.http"].is_a_bot()

    def action_view_statistics(self):
        self.check_singleton()
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "link_tracker.link_tracker_click_action_statistics"
        )
        action["domain"] = [("link_id", "=", self.id)]
        action["context"] = dict(self.env.context, create=False)
        return action

    def action_visit_page(self):
        self.check_singleton()
        return {
            "name": _("Visit Webpage"),
            "type": "ir.actions.act_url",
            "url": self.url,
            "target": "new",
        }

    @api.model
    def recent_links(self, sort_by, limit):
        # `search_read([])` returned all twenty fields, computed ones included,
        # for a dashboard that renders five of them.
        fields_to_read = [
            "code",
            "short_url",
            "title",
            "url",
            "label",
            "count",
            "create_date",
        ]
        if sort_by == "newest":
            return self.search_read(
                [], fields_to_read, order="create_date DESC, id DESC", limit=limit
            )
        if sort_by == "most-clicked":
            return self.search_read(
                [("count", "!=", 0)],
                fields_to_read,
                order="count DESC, id DESC",
                limit=limit,
            )
        if sort_by == "recently-used":
            return self.search_read(
                [("count", "!=", 0)],
                fields_to_read,
                order="write_date DESC, id DESC",
                limit=limit,
            )
        # Returning {'Error': ...} put a dict where the only caller does
        # `links.reverse()`, so a bad filter surfaced as a TypeError in the browser.
        raise UserError(_("“%s” is not a known sort order.", sort_by))

    @api.model
    def get_url_from_code(self, code):
        code_rec = (
            self.env["link.tracker.code"].sudo().search([("code", "=", code)], limit=1)
        )

        if not code_rec:
            return None

        return code_rec.link_id.redirected_url

    @api.model
    def _cron_update_titles(self, limit=200):
        """Backfill the titles `create` no longer fetches over the network."""
        trackers = self.sudo().search([("title", "=", False)], limit=limit)
        trackers |= (
            self.sudo()
            .search(
                [("title", "!=", False), ("url", "!=", False)],
                limit=limit,
            )
            .filtered(lambda tracker: tracker.title == tracker.url)
        )
        for tracker in trackers:
            title = self._get_title_from_url(tracker.url)
            if title and title != tracker.title:
                tracker.title = title


class LinkTrackerCode(models.Model):
    _name = "link.tracker.code"
    _description = "Link Tracker Code"
    _rec_name = "code"

    code = fields.Char(
        string="Short URL Code",
        required=True,
    )
    link_id = fields.Many2one(
        comodel_name="link.tracker",
        index=True,
        required=True,
        ondelete="cascade",
    )

    _code = models.Constraint(
        "unique( code )",
        "Code must be unique.",
    )

    @api.model
    def _get_random_code_strings(self, n=1):
        """``n`` codes that are unused, and unguessable.

        ``random`` is a Mersenne Twister: fine for a shuffle, not for a value
        whose only protection is that nobody can guess it.
        """
        if not n:
            return []
        size = LINK_TRACKER_MIN_CODE_LENGTH
        while True:
            code_propositions = [
                "".join(
                    secrets.choice(LINK_TRACKER_CODE_ALPHABET) for __ in range(size)
                )
                for __ in range(n)
            ]

            if len(set(code_propositions)) != n or self.sudo().search_count(
                [("code", "in", code_propositions)], limit=1
            ):
                size += 1
            else:
                return code_propositions


class LinkTrackerClick(models.Model):
    _name = "link.tracker.click"
    _rec_name = "link_id"
    _description = "Link Tracker Click"

    campaign_id = fields.Many2one(
        comodel_name="utm.campaign",
        related="link_id.campaign_id",
        string="UTM Campaign",
        ondelete="set null",
    )
    link_id = fields.Many2one(
        comodel_name="link.tracker",
        index=True,
        required=True,
        ondelete="cascade",
    )
    ip = fields.Char(string="Internet Protocol")
    country_id = fields.Many2one(comodel_name="res.country")

    def _prepare_click_values_from_route(self, **route_values):
        click_values = {
            fname: route_values[fname]
            for fname in self._fields
            if fname in route_values
        }
        if not click_values.get("country_id") and route_values.get("country_code"):
            click_values["country_id"] = (
                self.env["res.country"]
                .search([("code", "=", route_values["country_code"])], limit=1)
                .id
            )
        return click_values

    @api.model
    def add_click(self, code, *, tracker_code=None, **route_values):
        """Main API to add a click on a link.

        :param tracker_code: the already-resolved ``link.tracker.code``, when the
          caller has one. Every ``/r/`` route resolves the code to find its
          redirect target anyway, and used to pay for a second lookup here.
        """
        if tracker_code is None:
            tracker_code = self.env["link.tracker.code"].search(
                [("code", "=", code)], limit=1
            )
        if not tracker_code:
            return None

        route_values["link_id"] = tracker_code.link_id.id
        click_values = self._prepare_click_values_from_route(**route_values)

        return self.create(click_values)

    @api.model
    def _cron_clear_expired_ips(self, batch_size=10000):
        """Clear the stored IP of clicks older than the configured retention.

        ``link_tracker.click_ip_retention_days`` is unset by default, which keeps
        the previous behaviour: an IP is kept forever. Set it to a number of days
        to have this cron forget them.
        """
        days = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("link_tracker.click_ip_retention_days")
        )
        try:
            days = int(days or 0)
        except ValueError:
            _logger.warning(
                "link_tracker.click_ip_retention_days is not a number: %r, keeping IPs",
                days,
            )
            return
        if days <= 0:
            return
        cutoff = fields.Datetime.subtract(fields.Datetime.now(), days=days)
        expired = self.sudo().search(
            [("ip", "!=", False), ("create_date", "<", cutoff)], limit=batch_size
        )
        if expired:
            expired.write({"ip": False})
            _logger.info("link_tracker: cleared the IP of %s click(s)", len(expired))
