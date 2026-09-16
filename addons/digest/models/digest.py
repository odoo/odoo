import logging
from datetime import UTC, datetime
from itertools import batched
from typing import NamedTuple
from urllib.parse import urlencode

from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import api, fields, models, tools
from odoo.exceptions import AccessError
from odoo.fields import Command, Domain
from odoo.libs.datetime import timezone
from odoo.libs.numbers import float_round
from odoo.libs.web import urljoin as url_join
from odoo.tools import SQL

_logger = logging.getLogger(__name__)

#: Key under which `_get_kpi_data` parks its per-render aggregate memo on the
#: cursor. Scoped to one render and popped afterwards, so it cannot serve a
#: value computed for a different recipient or a different set of windows.
KPI_AGGREGATE_MEMO = "digest.kpi_aggregates"

#: Field-name prefixes that mark a boolean as a selectable KPI. ``x_kpi_`` and
#: ``x_studio_kpi_`` are the Studio spellings of a custom KPI.
KPI_PREFIXES = ("kpi_", "x_kpi_", "x_studio_kpi_")


class Periodicity(NamedTuple):
    """Everything a periodicity decides, in one place.

    Three separate ``if periodicity ==`` chains used to live in this file --
    one picking the next mailing date, one picking how long a recipient may be
    away before the digest slows down, one picking what it slows down *to*.
    They agreed by hand: the weekly chain spelled its idle window ``days=7``
    while its run delta was ``weeks=1``, and the run chain had no ``quarterly``
    branch at all, only a bare ``else``. A table makes a disagreement between
    the three a visible edit rather than a silent one.

    The ``periodicity`` selection is built from this table
    (``PERIODICITY_SELECTION``) rather than written beside it, so the two cannot
    disagree at all; ``test_periodicity_table_is_the_selection`` holds the
    remaining invariants -- that every fallback is itself a key, and that
    ``quarterly`` is the floor.
    """

    #: how far ahead ``next_run_date`` moves after a send
    run: relativedelta
    #: how long every recipient may go without a log before slowing down
    idle: relativedelta
    #: the periodicity to fall back to; ``quarterly`` is the floor
    slower: str
    #: the label the ``periodicity`` selection shows, exported for translation
    label: str


PERIODICITIES = {
    "daily": Periodicity(
        relativedelta(days=1), relativedelta(days=2), "weekly", "Daily"
    ),
    "weekly": Periodicity(
        relativedelta(weeks=1), relativedelta(weeks=1), "monthly", "Weekly"
    ),
    "monthly": Periodicity(
        relativedelta(months=1), relativedelta(months=1), "quarterly", "Monthly"
    ),
    "quarterly": Periodicity(
        relativedelta(months=3), relativedelta(months=3), "quarterly", "Quarterly"
    ),
}

#: The ``periodicity`` selection, built from the table rather than beside it.
#: Spelling it twice is how the run deltas and the idle windows drifted apart in
#: the first place, and a hand-written selection is one more copy to drift.
PERIODICITY_SELECTION = [(key, p.label) for key, p in PERIODICITIES.items()]


class DigestDigest(models.Model):
    """Periodic KPI email digest sent to a set of recipients."""

    _name = "digest.digest"
    _description = "Digest"
    _order = "name, id"

    # Digest description
    name = fields.Char(
        translate=True,
        required=True,
    )
    user_ids = fields.Many2many(
        comodel_name="res.users",
        string="Recipients",
        domain="[('share', '=', False)]",
    )
    periodicity = fields.Selection(
        selection=PERIODICITY_SELECTION,
        default="daily",
        required=True,
    )
    next_run_date = fields.Date(string="Next Mailing Date")
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Currency",
        readonly=False,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company.id,
    )
    is_subscribed = fields.Boolean(
        string="Is user subscribed",
        compute="_compute_is_subscribed",
    )
    state = fields.Selection(
        selection=[("activated", "Activated"), ("deactivated", "Deactivated")],
        string="Status",
        default="activated",
        readonly=True,
    )
    # First base-related KPIs
    kpi_res_users_connected = fields.Boolean(string="Connected Users")
    kpi_res_users_connected_value = fields.Integer(
        compute="_compute_kpi_res_users_connected_value"
    )
    kpi_mail_message_total = fields.Boolean(string="Messages Sent")
    kpi_mail_message_total_value = fields.Integer(
        compute="_compute_kpi_mail_message_total_value"
    )

    @api.depends("user_ids")
    @api.depends_context("uid")
    def _compute_is_subscribed(self):
        # The answer is the acting user's, so the cache key has to carry the
        # acting user: without `depends_context` a non-stored compute has ONE
        # cache entry per record for the whole transaction and the first
        # reader's answer is handed to everybody after it. Nothing in the send
        # path reads this today -- the only readers are the form view and the
        # tests, and a web request carries one uid -- so this closes a hazard
        # rather than a live defect.
        user = self.env.user
        for digest in self:
            digest.is_subscribed = user in digest.user_ids

    def _get_kpi_compute_parameters(self):
        """Get the parameters used to computed the KPI value.

        :return: ``(start, end, companies)``, the window bounds as naive-UTC
          strings and the companies to scope the KPI to.
        """
        companies = self.company_id
        if any(not digest.company_id for digest in self):
            # No company: we will use the current company to compute the KPIs
            companies |= self.env.company

        return (
            fields.Datetime.to_string(self.env.context.get("start_datetime")),
            fields.Datetime.to_string(self.env.context.get("end_datetime")),
            companies,
        )

    def _compute_kpi_res_users_connected_value(self):
        self._update_company_based_kpi(
            "res.users",
            "kpi_res_users_connected_value",
            date_field="login_date",
        )

    def _compute_kpi_mail_message_total_value(self):
        start, end, __ = self._get_kpi_compute_parameters()
        self.kpi_mail_message_total_value = self.env["mail.message"].search_count(
            [
                ("create_date", ">=", start),
                ("create_date", "<", end),
                ("subtype_id", "=", self.env.ref("mail.mt_comment").id),
                ("message_type", "in", ("comment", "email", "email_outgoing")),
            ]
        )

    @api.onchange("periodicity")
    def _onchange_periodicity(self):
        self.next_run_date = self._get_next_run_date(self.periodicity)

    @api.model_create_multi
    def create(self, vals_list):
        default_periodicity = None
        seeded = []
        for vals in vals_list:
            periodicity = vals.get("periodicity")
            if not periodicity:
                if default_periodicity is None:
                    default_periodicity = self.default_get(["periodicity"])[
                        "periodicity"
                    ]
                periodicity = default_periodicity
            # `periodicity not in PERIODICITIES` is left for super() to reject:
            # indexing the table here would answer a bad Selection value with a
            # bare KeyError instead of the ORM's own error, which names the
            # field and the allowed values.
            if vals.get("next_run_date") or periodicity not in PERIODICITIES:
                seeded.append(vals)
                continue
            # Seed the date in the create values rather than writing it back
            # afterwards: the old post-create loop cost one UPDATE per digest
            # and made `create` non-atomic for anything watching the column.
            seeded.append(
                {**vals, "next_run_date": self._get_next_run_date(periodicity)}
            )
        return super().create(seeded)

    # ------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------

    def action_subscribe(self):
        if self.env.user._is_internal() and self.env.user not in self.user_ids:
            self._action_subscribe_users(self.env.user)

    def _action_subscribe_users(self, users):
        """Private method to manage subscriptions. Done as sudo() to speedup
        computation and avoid ACLs issues."""
        self.sudo().user_ids |= users

    def action_unsubscribe(self):
        if self.env.user._is_internal() and self.env.user in self.user_ids:
            self._action_unsubscribe_users(self.env.user)

    def _action_unsubscribe_users(self, users):
        """Private method to manage subscriptions. Done as sudo() to speedup
        computation and avoid ACLs issues."""
        self.sudo().user_ids -= users

    def action_activate(self):
        self.state = "activated"

    def action_deactivate(self):
        self.state = "deactivated"

    def action_set_periodicity(self, periodicity):
        self.periodicity = periodicity

    def action_send(self):
        """Send digests emails to all the registered users."""
        return self._action_send(update_periodicity=True)

    def action_send_manual(self):
        """Manually send digests emails to all registered users. In that case
        do not update periodicity as this is not an automation rule that could
        be considered as unwanted spam."""
        return self._action_send(update_periodicity=False)

    def _action_send(self, update_periodicity=True):
        """Send digests email to all the registered users.

        :param bool update_periodicity: if True, check user logs to update
          periodicity of digests. Purpose is to slow down digest whose users
          do not connect to avoid spam;
        """
        to_slowdown = (
            self._get_digests_to_slowdown() if update_periodicity else self.browse()
        )

        for digest in self:
            for user in digest.user_ids:
                try:
                    digest.with_context(
                        digest_slowdown=digest in to_slowdown,
                        lang=user.lang,
                        # the header date and every `format_*` in the body are
                        # the recipient's, not the sender's
                        tz=user.tz,
                    )._action_send_to_user(user, tips_count=1)
                except Exception:
                    # A KPI's compute can be arbitrary end-user-authored logic
                    # (Studio KPIs, see `KPI_PREFIXES`); one broken formula
                    # must not cost every other digest in this batch its
                    # mail, since `_cron_send_digest_email` only commits
                    # between whole batches.
                    _logger.exception(
                        "Failed to send digest %r to %s", digest.name, user.login
                    )
                    continue
            if digest in to_slowdown:
                digest.periodicity = digest._get_next_periodicity()[0]
            digest.next_run_date = digest._get_next_run_date()

    def _action_send_to_user(self, user, tips_count=1, consume_tips=True):
        """Render and send the digest email to a single recipient.

        :param res.users user: The recipient.
        :param int tips_count: Number of tips to include in the email.
        :param bool consume_tips: Whether to mark the included tips as consumed for `user`.
        :return: True
        """
        unsubscribe_token = self._get_unsubscribe_token(user.id)

        rendered_body = self.env["mixin.mail.render"]._render_template(
            "digest.digest_mail_main",
            "digest.digest",
            self.ids,
            engine="qweb_view",
            add_context={
                "title": self.name,
                "top_button_label": self.env._("Connect"),
                "top_button_url": self.get_base_url(),
                "company": user.company_id,
                "user": user,
                "unsubscribe_token": unsubscribe_token,
                "tips_count": tips_count,
                "formatted_date": tools.format_date(
                    self.env,
                    fields.Date.context_today(self),
                    date_format="MMMM dd, yyyy",
                ),
                "display_mobile_banner": True,
                "kpi_data": self._get_kpi_data(user.company_id, user),
                "tips": self._get_tips(
                    user.company_id, user, tips_count=tips_count, consumed=consume_tips
                ),
                "preferences": self._get_preferences(user.company_id, user),
            },
            options={
                "preserve_comments": True,
                "post_process": True,
            },
        )[self.id]
        full_mail = self.env["mixin.mail.render"]._render_encapsulate(
            "digest.digest_mail_layout",
            rendered_body,
            add_context={
                "company": user.company_id,
                "user": user,
            },
        )
        # create a mail_mail based on values, without attachments
        unsub_params = urlencode(
            {
                "token": unsubscribe_token,
                "user_id": user.id,
            }
        )
        unsub_url = url_join(
            self.get_base_url(),
            f"/digest/{self.id}/unsubscribe_oneclick?{unsub_params}",
        )
        mail_values = {
            "auto_delete": True,
            "author_id": self.env.user.partner_id.id,
            "body_html": full_mail,
            "email_from": (
                self.company_id.partner_id.email_formatted
                or self.env.user.email_formatted
                or self.env.ref("base.user_root").email_formatted
            ),
            "email_to": user.email_formatted,
            # Add headers that allow the MUA to offer a one click button to unsubscribe (requires DKIM to work)
            "headers": {
                "List-Unsubscribe": f"<{unsub_url}>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
                "X-Auto-Response-Suppress": "OOF",  # avoid out-of-office replies from MS Exchange
            },
            "state": "outgoing",
            "subject": f"{user.company_id.name}: {self.name}",
        }
        self.env["mail.mail"].sudo().create(mail_values)
        return True

    @api.model
    def _cron_send_digest_email(self):
        digests = self.search(
            [("next_run_date", "<=", fields.Date.today()), ("state", "=", "activated")]
        )
        commit_progress = self.env["ir.cron"]._commit_progress
        commit_progress(0, remaining=len(digests))
        # Ten, not the 100--1000 of coding_guidelines §11.7: a batch here is not
        # ten records but ten *mailings*, each rendering one email per recipient
        # at roughly seventy queries a head. Ten digests of fifty recipients is
        # already ~35k queries in the batch's transaction; a hundred would hold
        # the mail_mail write locks for minutes.
        for batch_ids in batched(digests.ids, 10, strict=False):
            self.browse(batch_ids).action_send()
            if not commit_progress(processed=len(batch_ids)):
                # budget exhausted; the cron reschedules itself and the digests
                # left over are still due on the next pass.
                break

    def _get_unsubscribe_token(self, user_id):
        """Generate a secure hash for this digest and user. It allows to
        unsubscribe from a digest while keeping some security in that process.

        :param int user_id: ID of the user to unsubscribe
        """
        return tools.hmac(self.env(su=True), "digest-unsubscribe", (self.id, user_id))

    # ------------------------------------------------------------
    # KPIS
    # ------------------------------------------------------------

    def _get_kpi_data(self, company, user):
        """Compute KPIs to display in the digest template. It is expected to be
        a list of KPIs, each containing values for 3 columns display.

        :return: result [{
            'kpi_name': 'kpi_mail_message',
            'kpi_fullname': 'Messages',  # translated
            'kpi_action': 'crm.crm_lead_action_pipeline',  # xml id of an action to execute
            'kpi_col1': {
                'value': '12.0',
                'margin': 32.36,
                'col_subtitle': 'Yesterday',  # translated
            },
            'kpi_col2': { ... },
            'kpi_col3':  { ... },
        }, { ... }]"""
        self.check_singleton()
        kpi_names = self._get_fields_kpi()
        kpi_actions = self._get_kpi_actions(company, user)
        timeframes = self._get_timeframes(company)
        # Every KPI is asked for the same six windows. Publishing them lets
        # `_update_company_based_kpi` answer all six from one scan instead of
        # six, and the memo below is what carries that answer across the six
        # separate compute-field reads the loop still has to make.
        all_windows = tuple(
            (fields.Datetime.to_string(start), fields.Datetime.to_string(end))
            for __, pair in timeframes
            for start, end in pair
        )
        memo = {}
        self.env.cr.cache[KPI_AGGREGATE_MEMO] = memo
        ir_model_fields = self.env["ir.model.fields"]
        kpis = {
            name: {
                "kpi_name": name,
                "kpi_fullname": ir_model_fields._get(
                    self._name, name
                ).field_description,
                "kpi_action": kpi_actions.get(name),
                "kpi_col1": {},
                "kpi_col2": {},
                "kpi_col3": {},
            }
            for name in kpi_names
        }
        # A KPI the recipient may not read raises AccessError once and is dropped
        # for good. The previous shape retried it in every one of the six windows,
        # so a denied KPI paid its group resolution and record-rule lookup six
        # times over to reach the same answer.
        denied = set()

        digest = self.with_context(digest_windows=all_windows)
        try:
            kpis = digest._update_kpi_columns(
                kpis, kpi_names, timeframes, company, user, denied
            )
        finally:
            self.env.cr.cache.pop(KPI_AGGREGATE_MEMO, None)

        return [kpi for name, kpi in kpis.items() if name not in denied]

    def _update_kpi_columns(self, kpis, kpi_names, timeframes, company, user, denied):
        """Read every KPI over every window and fill the three display columns."""
        for col_index, (tf_name, (current, previous)) in enumerate(timeframes, start=1):
            for name in kpi_names:
                if name in denied:
                    continue
                value_field = f"{name}_value"
                try:
                    value = self._get_kpi_value(value_field, current, company, user)
                    previous_value = self._get_kpi_value(
                        value_field, previous, company, user
                    )
                except AccessError:
                    # no access rights -> just skip that KPI in that user's digest email
                    denied.add(name)
                    continue

                margin = self._get_margin_value(value, previous_value)
                field_type = self._fields[value_field].type
                if field_type == "monetary":
                    value = self._format_currency_amount(
                        tools.misc.format_decimalized_amount(value),
                        company.currency_id,
                    )
                elif field_type == "float":
                    value = "%.2f" % value

                kpis[name][f"kpi_col{col_index}"].update(
                    {
                        "value": value,
                        "margin": margin,
                        "col_subtitle": tf_name,
                    }
                )

        return kpis

    def _get_kpi_value(self, value_field, window, company, user):
        """Read one ``kpi_*_value`` field over one time window, as ``user``.

        The window reaches the compute through the context rather than through
        an argument, which the ORM cannot see: a ``kpi_*_value`` field declares
        no ``depends_context``, so its cache holds ONE entry per record for the
        whole transaction and the second window would read the first one's
        answer back. Declaring the dependency is not available here -- the
        field is defined by whichever addon contributes the KPI, thirteen of
        them across three repositories -- so the cache entry is dropped by hand
        instead, and dropped even when the compute raised, so a denied KPI
        leaves no failure marker behind for the next reader.
        """
        digest = (
            self.with_context(
                start_datetime=window[0],
                end_datetime=window[1],
            )
            .with_user(user)
            .with_company(company)
        )
        try:
            return digest[value_field]
        finally:
            # invalidate_recordset, NOT invalidate_model: the model-wide form
            # also discards the KPI values of every other digest.digest record,
            # which in a cron run is every digest already computed this pass.
            # flush=False because a `kpi_*_value` is never stored, so there is
            # nothing to write -- and the default flush would RE-RUN a compute
            # still pending after it raised, evaluating a denied KPI twice.
            digest.invalidate_recordset([value_field], flush=False)

    def _get_unloaded_tip_ids(self):
        # A tip renders its module's models; while modules are still loading,
        # an installed module's tip exists before its models do.
        loaded = self.env.registry.loaded_modules
        if not loaded:
            return []
        return (
            self.env["ir.model.data"]
            .sudo()
            .search_fetch(
                [("model", "=", "digest.tip"), ("module", "not in", list(loaded))],
                ["res_id"],
            )
            .mapped("res_id")
        )

    def _get_tips(self, company, user, tips_count=1, consumed=True):
        tips = self.env["digest.tip"].search(
            [
                ("user_ids", "not in", user.id),
                ("id", "not in", self._get_unloaded_tip_ids()),
                "|",
                ("group_id", "in", user.all_group_ids.ids),
                ("group_id", "=", False),
            ],
            limit=tips_count,
        )
        tip_descriptions = [
            tools.html_sanitize(
                self.env["mixin.mail.render"]
                .sudo()
                ._render_template(
                    tip.tip_description,
                    "digest.tip",
                    tip.ids,
                    engine="qweb",
                    options={"post_process": True},
                )[tip.id]
            )
            for tip in tips
        ]
        if consumed:
            # Command.link, not `tips.user_ids += user`: the augmented form reads
            # the UNION of every tip's recipients and writes that union back to
            # each of them, so with tips_count > 1 tip A silently acquires tip
            # B's audience and neither is ever offered to those users again.
            tips.sudo().user_ids = [Command.link(user.id)]
        return tip_descriptions

    def _get_kpi_actions(self, company, user):
        """Give an optional action to display in digest email linked to some KPIs.

        :returns: key: kpi name (field name), value: an action that will be
          concatenated with /odoo/action-{action}
        :rtype: dict
        """
        return {}

    def _get_preferences(self, company, user):
        """Give an optional text for preferences, like a shortcut for configuration.

        :returns: html to put in template
        :rtype: str
        """
        preferences = []
        if self.env.context.get("digest_slowdown"):
            __, new_perioridicy_str = self._get_next_periodicity()
            preferences.append(
                self.env._(
                    "We have noticed you did not connect these last few days. We have automatically switched your preference to %(new_perioridicy_str)s Digests.",
                    new_perioridicy_str=new_perioridicy_str,
                )
            )
        elif self.periodicity == "daily" and user.has_group("base.group_erp_manager"):
            preferences.append(
                Markup(
                    '<p>%s<br /><a href="%s" target="_blank" style="color:#017e84; font-weight: bold;">%s</a></p>'
                )
                % (
                    self.env._("Prefer a broader overview?"),
                    f"/digest/{self.id:d}/set_periodicity?periodicity=weekly",
                    self.env._("Switch to weekly Digests"),
                )
            )
        if user.has_group("base.group_erp_manager"):
            preferences.append(
                Markup(
                    '<p>%s<br /><a href="%s" target="_blank" style="color:#017e84; font-weight: bold;">%s</a></p>'
                )
                % (
                    self.env._("Want to customize this email?"),
                    f"/odoo/{self._name}/{self.id:d}",
                    self.env._("Choose the metrics you care about"),
                )
            )

        return preferences

    def _get_next_run_date(self, periodicity=None):
        """Date of the next mailing for ``periodicity`` (default: this digest's)."""
        if periodicity is None:
            self.check_singleton()
            periodicity = self.periodicity
        return fields.Date.today() + PERIODICITIES[periodicity].run

    def _get_timeframes(self, company):
        """The three (current, previous) windows the mail compares, in naive UTC.

        The bounds are handed straight to ``Datetime.to_string`` by
        ``_get_kpi_compute_parameters`` and land in a domain against naive-UTC
        columns, so they have to *be* naive UTC. Doing the arithmetic in the
        company's calendar timezone keeps a window that spans a DST change the
        right length; returning it in that timezone would shift every bound by
        the offset, which is what used to happen -- a Brussels company read a
        "last 24 hours" that ended two hours in the future and lost the first
        two hours of the day it was reporting on.
        """
        start_datetime = datetime.now(UTC)
        tz_name = company.resource_calendar_id.tz
        if tz_name:
            start_datetime = start_datetime.astimezone(timezone(tz_name))

        def window(start_delta, end_delta=None):
            start = start_datetime + start_delta
            end = start_datetime + end_delta if end_delta else start_datetime
            return (
                start.astimezone(UTC).replace(tzinfo=None),
                end.astimezone(UTC).replace(tzinfo=None),
            )

        return [
            (
                self.env._("Last 24 hours"),
                (
                    window(relativedelta(days=-1)),
                    window(relativedelta(days=-2), relativedelta(days=-1)),
                ),
            ),
            (
                self.env._("Last 7 Days"),
                (
                    window(relativedelta(weeks=-1)),
                    window(relativedelta(weeks=-2), relativedelta(weeks=-1)),
                ),
            ),
            (
                self.env._("Last 30 Days"),
                (
                    window(relativedelta(months=-1)),
                    window(relativedelta(months=-2), relativedelta(months=-1)),
                ),
            ),
        ]

    # ------------------------------------------------------------
    # FORMATTING / TOOLS
    # ------------------------------------------------------------

    def _update_company_based_kpi(
        self,
        model,
        digest_kpi_field,
        date_field="create_date",
        additional_domain=None,
        sum_field=None,
    ):
        """Generic method that computes the KPI on a given model.

        :param model: Model on which we will compute the KPI
            This model must have a "company_id" field
        :param digest_kpi_field: Field name on which we will write the KPI
        :param date_field: Field used for the date range
        :param additional_domain: Additional domain
        :param sum_field: Field to sum to obtain the KPI,
            if None it will count the number of records
        """
        start, end, companies = self._get_kpi_compute_parameters()
        extra_domain = Domain(additional_domain) if additional_domain else Domain.TRUE

        values_per_company = self._read_kpi_over_windows(
            digest_kpi_field,
            model,
            date_field,
            extra_domain,
            sum_field,
            companies,
        )
        if values_per_company is None:
            base_domain = (
                Domain(
                    [
                        ("company_id", "in", companies.ids),
                        (date_field, ">=", start),
                        (date_field, "<", end),
                    ]
                )
                & extra_domain
            )
            values = self.env[model]._read_group(
                domain=base_domain,
                groupby=["company_id"],
                aggregates=[f"{sum_field}:sum"] if sum_field else ["__count"],
            )
            values_per_company = {company.id: agg for company, agg in values}
        else:
            values_per_company = {
                company_id: per_window[(start, end)]
                for company_id, per_window in values_per_company.items()
            }

        for digest in self:
            company = digest.company_id or self.env.company
            digest[digest_kpi_field] = values_per_company.get(company.id, 0)

    def _read_kpi_over_windows(
        self, digest_kpi_field, model, date_field, extra_domain, sum_field, companies
    ):
        """Answer all six digest windows from ONE scan, or ``None`` to fall back.

        The six windows a digest compares are known before any KPI is read, so
        the six range aggregates they used to cost are one scan of their union
        with six ``FILTER`` clauses over it. Measured on ``crm.lead`` at 50,000
        rows across sixty days, best of twelve with the cache dropped between
        runs:

            six `_read_group` calls   7 queries   9.05 ms
            one filtered aggregate    1 query     7.27 ms

        Both axes, not just the query count -- and the query count is the one
        that misleads here. An hour-bucketed ``_read_group`` also collapses to
        one query and was measured at **16.54 ms**, twice the cost of the six it
        replaces, because grouping fifty thousand rows into 1,440 buckets is
        more work than six index range scans. It also buckets in the *context*
        timezone, so with ``tz`` set (which `_action_send` now does) an
        Asia/Kolkata recipient would get buckets offset half an hour from the
        naive-UTC bounds. That approach was measured and rejected; this one goes
        through ``_search``, so record rules still apply.

        Returns ``{company_id: {(start, end): value}}``, or ``None`` when there
        is no window list in the context -- a KPI field read outside
        `_get_kpi_data` still works, on the one-window path.
        """
        windows = self.env.context.get("digest_windows")
        memo = self.env.cr.cache.get(KPI_AGGREGATE_MEMO)
        if not windows or memo is None:
            return None

        # Every column this builds SQL for has to BE a column. `res.users`'s
        # own `login_date` is the counterexample, and it lives in this module:
        # it is a non-stored related through the `log_ids` One2many, so
        # `_field_to_sql` refuses it outright ("... because log_ids is not a
        # Many2one"). `_read_group` copes because the domain optimiser can turn
        # the related path into a join; a hand-built aggregate cannot. Anything
        # not stored takes the one-window path, which is still correct -- only
        # slower -- and `test_one_scan_answers_every_window_with_the_same_numbers`
        # is what says the two agree.
        Model = self.env[model]
        needed = [date_field, "company_id", *filter(None, [sum_field])]
        if not all(Model._fields[name].store for name in needed):
            return None

        # Keyed by the KPI FIELD, which is unique per KPI and always carries the
        # same domain, so two KPIs over the same model cannot read each other's
        # answer however similar their domains look.
        key = (
            digest_kpi_field,
            model,
            date_field,
            sum_field,
            windows,
            tuple(companies.ids),
            self.env.uid,
            self.env.su,
        )
        if key in memo:
            return memo[key]

        lo = min(start for start, __ in windows)
        hi = max(end for __, end in windows)
        query = Model._search(
            Domain(
                [
                    ("company_id", "in", companies.ids),
                    (date_field, ">=", lo),
                    (date_field, "<", hi),
                ]
            )
            & extra_domain
        )

        date_sql = Model._field_to_sql(Model._table, date_field, query)
        company_sql = Model._field_to_sql(Model._table, "company_id", query)
        if sum_field:
            value_sql = Model._field_to_sql(Model._table, sum_field, query)
            aggregate = lambda window: SQL(  # noqa: E731  one shape, used six times
                "COALESCE(SUM(%s) FILTER (WHERE %s >= %s AND %s < %s), 0)",
                value_sql,
                date_sql,
                window[0],
                date_sql,
                window[1],
            )
        else:
            aggregate = lambda window: SQL(  # noqa: E731  one shape, used six times
                "COUNT(*) FILTER (WHERE %s >= %s AND %s < %s)",
                date_sql,
                window[0],
                date_sql,
                window[1],
            )

        sql = SQL(
            "%s GROUP BY %s",
            query.select(company_sql, *(aggregate(w) for w in windows)),
            company_sql,
        )
        # `env.execute_query`, not `cr.execute`: it flushes the fields the SQL
        # touches first (`Environment.flush_query`). The ORM defers writes, so
        # reading behind its back is how a KPI misses a record created in the
        # same transaction -- `_read_group`, the call this replaces, flushes for
        # the same reason.
        result = {
            row[0]: dict(zip(windows, row[1:], strict=True))
            for row in self.env.execute_query(sql)
        }
        memo[key] = result
        return result

    @api.model
    def _get_kpi_boolean_names(self):
        """Names of every ``kpi_*`` boolean any installed module contributes."""
        return [
            field_name
            for field_name, field in self._fields.items()
            if field.type == "boolean" and field_name.startswith(KPI_PREFIXES)
        ]

    def _get_fields_kpi(self):
        """Names of the ``kpi_*`` booleans this digest has switched on."""
        return [name for name in self._get_kpi_boolean_names() if self[name]]

    def _get_margin_value(self, value, previous_value=0.0):
        """Percentage change from ``previous_value`` to ``value``.

        The guard used to require BOTH sides to be non-zero, and the
        ``value != 0.0`` half of that was wrong: a KPI that fell to nothing is
        a plain -100%, it falls straight out of the formula, and suppressing it
        hid the single most newsworthy movement a KPI can make.

        A **zero previous** value is a different case and keeps returning 0.0,
        which the template reads as "no badge". Growth from zero has no
        percentage -- 0 -> 1 and 0 -> 1000 would both read 100% -- and this is
        the convention the rest of the tree already follows:
        ``account._get_column_percent_comparison_data`` returns a
        muted *n/a* when the compared period is zero rather than inventing a
        figure. An earlier draft of this method returned 100% there; that was
        an invention, and it is not made here.
        """
        if value == previous_value or not previous_value:
            return 0.0
        return float_round(
            (value - previous_value) / previous_value * 100, precision_digits=2
        )

    def _get_digests_to_slowdown(self):
        """Digests whose recipients have all been away for a full period.

        Sending to a mailbox nobody reads is the spam this slows down. One
        ``_read_group`` for the whole recordset, not one ``search_count`` per
        digest: the count was only ever compared against zero and
        the loop made the cron's cost linear in the number of digests.
        """
        now = fields.Datetime.now()
        recipients = self.user_ids
        last_log_per_user = (
            dict(
                self.env["res.users.log"]
                .sudo()
                ._read_group(
                    [("create_uid", "in", recipients.ids)],
                    groupby=["create_uid"],
                    aggregates=["create_date:max"],
                )
            )
            if recipients
            else {}
        )

        to_slowdown = self.browse()
        for digest in self:
            limit_dt = now - PERIODICITIES[digest.periodicity].idle
            if not any(
                (last_log := last_log_per_user.get(user)) and last_log >= limit_dt
                for user in digest.user_ids
            ):
                to_slowdown += digest
        return to_slowdown

    def _get_next_periodicity(self):
        """``(value, translated label)`` of the periodicity to slow down to."""
        slower = PERIODICITIES[self.periodicity].slower
        # Read the label off the field's own (translated) selection instead
        # of a second hand-written dict keyed by today's three `slower`
        # values: a `PERIODICITIES` entry whose `slower` isn't one of those
        # hardcoded keys used to raise a KeyError here, uncaught by
        # test_periodicity_table_is_the_selection. This can't fall out of
        # sync with the table, because it's the table.
        selection_labels = dict(
            self._fields["periodicity"]._description_selection(self.env)
        )
        return slower, selection_labels[slower].lower()

    def _format_currency_amount(self, amount, currency_id):
        symbol = currency_id.symbol or ""
        if currency_id.position == "before":
            return f"{symbol}{amount}"
        return f"{amount}{symbol}"
