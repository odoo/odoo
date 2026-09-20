import logging
from bisect import bisect_left, bisect_right

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

OPEN_STATES = ("new", "running")
CLOSED_STATES = ("done", "cancelled")
STATE_TRANSITIONS = {
    "new": {"running", "done", "cancelled"},
    "running": {"new", "done", "cancelled"},
    "done": {"new", "running", "cancelled"},
    "cancelled": {"new"},
}
# The states a log may be born in. `cancelled` is not one: its only legal exit is
# back to `new`, so a row created there is a row the transition table would never
# have produced. Producers do book rows straight into `done` -- a settled vendor
# bill, a finished maintenance move -- and into `running`, so those stay open.
ENTRY_STATES = frozenset({"new", "running", "done"})


class ResourceAssetLog(models.Model):
    _name = "resource.asset.log"
    _inherit = ["mixin.mail.thread", "mixin.mail.activity"]
    _description = "Asset Log"
    _order = "date desc, id desc"
    _check_company_auto = True

    company_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_company_id",
        store=True,
        readonly=False,
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    vendor_id = fields.Many2one(comodel_name="res.partner")
    asset_id = fields.Many2one(
        comodel_name="resource.asset",
        index=True,
        ondelete="cascade",
        check_company=True,
        help="Asset this log entry is related to",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        ondelete="restrict",
    )
    product_category_id = fields.Many2one(
        related="product_id.categ_id",
        string="Product Category",
    )
    log_type = fields.Selection(
        selection="_selection_log_type",
        compute="_compute_log_type",
        store=True,
        readonly=False,
        help="Taken from the product's category when the log is written. Editing a "
        "category's own log type afterwards must not rewrite the meaning of "
        "logs already booked under it.",
    )
    active = fields.Boolean(default=True)
    state = fields.Selection(
        selection=[
            ("new", "New"),
            ("running", "Running"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        default="new",
        group_expand=True,
        tracking=True,
    )
    date = fields.Date(
        default=fields.Date.context_today,
        help="Date when the cost has been executed",
    )
    source = fields.Selection(
        selection=[("manual", "Manual")],
        default="manual",
        required=True,
        help="Which producer wrote this row. Every asset cost and every odometer "
        "reading in the system is a log line, so the ledger has one provenance "
        "axis. Each producing module adds its own value through selection_add, "
        "so a value exists here only where something writes it.",
    )
    amount = fields.Monetary(
        string="Cost",
        tracking=True,
    )
    inv_ref = fields.Char(string="Vendor Reference")
    notes = fields.Text()
    odometer = fields.Float(
        string="Odometer Value",
        help="Odometer measure of the asset at the moment of this log",
    )
    odometer_uom_name = fields.Char(
        related="asset_id.odometer_uom_name",
        string="Odometer Unit",
    )

    def _selection_log_type(self):
        category_field = self.env["product.category"]._fields["log_type"]
        return category_field.get_description(self.env)["selection"]

    @api.depends("asset_id")
    def _compute_company_id(self):
        """A log belongs to its asset's company, not to whoever books it.

        The ledger invariant is `_check_ledger_does_not_span_companies`: one
        asset, one company. A `default=lambda self: self.env.company` cannot
        uphold it, because the acting user's company has nothing to do with the
        asset's. The nightly GPS cron runs as OdooBot in company 1 against a
        fleet owned by company 2, so every snapshot it ever booked was refused;
        and the 19.0.1.20.0 migration repaired 32 rows an import had booked the
        same way. Repairing the rows without moving the company to its source
        only leaves the next import free to make them again.

        The dependency is deliberately the coarse `asset_id`, not
        `asset_id.company_id`: this seeds a value, it does not track one. A log
        is an accounting row whose currency follows its company, so re-pointing
        a whole stored ledger because someone edited the asset months later is
        not a recompute anybody asked for. Re-pointing a log at a different
        asset is, and that is what this fires on.

        Not `precompute=True`: the framework refuses it for a compute whose
        dependency is a plain field, and `asset_id` is one, so it only bought a
        `cannot be precomputed` warning on every registry load. The company is
        written just after the insert instead, which the constraints below and
        `_check_company_auto` both run after.

        A company-less asset imposes nothing -- products are shared by default
        and core's `stock.lot._compute_company_id` copies that emptiness onto
        the lot -- so those fall back to the acting company, which is the case
        the constraint already exempts by ignoring empty companies.
        """
        for log in self:
            if log.asset_id.company_id:
                log.company_id = log.asset_id.company_id
            elif not log.company_id:
                log.company_id = self.env.company

    @api.depends("product_category_id")
    def _compute_log_type(self):
        for log in self:
            # Keep what the producer declared when the category types nothing:
            # a bill line with no product has no category, and a row that lands
            # untyped is counted by count_logs_all and by no per-type bucket.
            log.log_type = log.product_category_id.log_type or log.log_type

    @api.constrains("company_id", "asset_id")
    def _check_ledger_does_not_span_companies(self):
        """One asset, one company's ledger.

        `_check_company_auto` binds a log to its asset's company only when the
        asset HAS one, and a company-less asset is the ordinary case: products
        are shared by default, and core's `stock.lot._compute_company_id`
        copies the product's empty company onto the lot. Without this check a
        shared asset accepts logs from every company at once, and two things
        break: the card balances subtract a plain `amount:sum` from a
        lot-currency opening balance, adding francs to pesos as if they were
        the same unit; and `_check_odometer_sequence` refuses a reading against
        a neighbour the writer is not allowed to read, disclosing its value and
        date in the message.

        Two different things trip this, and telling a reader the wrong one
        sends them hunting through data that is fine. Either the stored ledger
        was already split before this write touched it -- nothing the writer
        did, and re-saving will not clear it -- or the stored ledger is whole
        and the rows being saved are the ones landing elsewhere, which the
        writer can fix by booking them in the ledger's company. So the records
        under validation are weighed apart from the rest of the ledger rather
        than lumped in with it.
        """
        if not self.asset_id:
            return
        # sudo: the whole point is to see the logs the writer cannot. The
        # message names no record from another company, only that there is one.
        settled_by_asset = dict(
            self.sudo()._read_group(
                [("asset_id", "in", self.asset_id.ids), ("id", "not in", self.ids)],
                ["asset_id"],
                ["company_id:array_agg"],
            )
        )
        for asset in self.asset_id:
            settled = {
                company_id
                for company_id in settled_by_asset.get(asset, ())
                if company_id
            }
            incoming = {
                log.company_id.id
                for log in self
                if log.asset_id == asset and log.company_id
            }
            if len(settled) > 1:
                self._log_ledger_company_split(asset)
                raise ValidationError(
                    self.env._(
                        "%(asset)s already has logs booked in another company, "
                        "from before this edit. An asset's ledger has to stay "
                        "inside one company: its balances are kept in a single "
                        "currency and its odometer readings are compared "
                        "against each other. Nothing you entered caused this "
                        "and re-saving will not clear it -- the existing logs "
                        "have to be moved to one company first. The details are "
                        "in the server log; ask an administrator to look.",
                        asset=asset.display_name,
                    )
                )
            if len(settled | incoming) > 1:
                self._log_ledger_company_conflict(asset, settled)
                raise ValidationError(
                    self.env._(
                        "%(asset)s keeps its ledger in one company, and this "
                        "entry is being booked into a different one. An asset's "
                        "ledger has to stay inside one company: its balances "
                        "are kept in a single currency and its odometer "
                        "readings are compared against each other. Book the "
                        "entry in the company that already holds the ledger, or "
                        "move the whole ledger across first. The details are in "
                        "the server log; ask an administrator to look.",
                        asset=asset.display_name,
                    )
                )

    def _log_ledger_company_split(self, asset):
        """Name the offending logs in the server log, never in the message.

        The reader is stuck: the rows they have to hear about are, by
        definition, ones their own company cannot see, and spelling them out in
        a ValidationError would hand every writer the ids, dates and owning
        companies of another company's ledger. So the message stays mute about
        them and the detail goes here instead, where the administrator who can
        actually move the rows is already looking, and where saying which log
        sits in which company discloses nothing the reader did not already have
        the right to read.
        """
        # sudo: same reason as the caller -- the whole point is the rows the
        # writer cannot see. Nothing read here reaches the user-facing message.
        logs = (
            self.env["resource.asset.log"]
            .sudo()
            .search([("asset_id", "=", asset.id)], order="company_id, id")
        )
        by_company = {}
        for log in logs:
            by_company.setdefault(log.company_id, self.env["resource.asset.log"])
            by_company[log.company_id] |= log
        _logger.warning(
            "Asset %s (id=%s) has logs booked across %d companies, so every "
            "save of it fails. Move them into one company -- the minority side "
            "is usually an import that took the session's company instead of "
            "the asset's:\n%s",
            asset.display_name,
            asset.id,
            len(by_company),
            "\n".join(
                f"  company {company.id or '-'} ({company.display_name or 'unset'}): "
                f"{len(company_logs)} log(s), ids {company_logs.ids}"
                for company, company_logs in by_company.items()
            ),
        )

    def _log_ledger_company_conflict(self, asset, settled):
        """Name the rows being saved, not the ledger they disagree with.

        `_log_ledger_company_split` searches the stored logs, which is right
        when the split is already in the database and useless here: in this
        case the stored ledger is whole, and searching it reports one company
        and no problem at all. The half worth naming is the incoming one --
        which records of this write are landing elsewhere, and where the ledger
        they belong to actually sits.
        """
        # sudo: same reason as `_log_ledger_company_split` -- the ledger's own
        # company may be one the writer cannot read, and nothing found here
        # reaches the user-facing message.
        companies = self.env["res.company"].sudo().browse(sorted(settled))
        pending = self.filtered(lambda log: log.asset_id == asset)
        _logger.warning(
            "Asset %s (id=%s) keeps its ledger in %s, and this write books "
            "%d log(s) into another company, so the save is refused. Book them "
            "in the ledger's company, or move the ledger across first:\n%s",
            asset.display_name,
            asset.id,
            ", ".join(
                f"company {company.id} ({company.display_name})"
                for company in companies
            )
            or "no company",
            len(pending),
            "\n".join(
                f"  log id={log.id}: company {log.company_id.id or '-'} "
                f"({log.company_id.display_name or 'unset'})"
                for log in pending
            ),
        )

    @api.depends("asset_id", "product_id", "date")
    def _compute_display_name(self):
        for log in self:
            parts = [
                part
                for part in (
                    log.asset_id.display_name,
                    log.product_id.display_name,
                    fields.Date.to_string(log.date) if log.date else None,
                )
                if part
            ]
            log.display_name = " / ".join(parts) or self.env._("New Log")

    @api.model_create_multi
    def create(self, vals_list):
        self._check_entry_state(vals_list)
        logs = super().create(vals_list)
        logs.asset_id._sync_odometer_meter()
        return logs

    @api.model
    def _check_entry_state(self, vals_list):
        """`write` has enforced `STATE_TRANSITIONS` all along; `create` did not,
        so an import or a producer could seed a row in a state the machine would
        never have let it reach."""
        for vals in vals_list:
            state = vals.get("state")
            if state and state not in ENTRY_STATES:
                raise UserError(
                    self.env._(
                        "A log cannot be created in state %(state)s. Create it "
                        "in one of %(allowed)s and move it from there.",
                        state=state,
                        allowed=", ".join(sorted(ENTRY_STATES)),
                    )
                )

    def write(self, vals):
        if "state" in vals:
            self._check_state_transition(vals["state"])
        assets_before = self.asset_id
        res = super().write(vals)
        if vals.keys() & {"odometer", "date", "asset_id", "active", "state"}:
            (assets_before | self.asset_id)._sync_odometer_meter()
        return res

    def unlink(self):
        """A deleted reading rolls the ledger's newest reading back, so the
        meter has to follow it down. `create` and `write` already re-sync;
        without this the two odometers disagree forever and every consumer of
        the meter -- a maintenance plan's distance trigger, telemetry -- keeps
        the reading of a log that no longer exists."""
        assets_before = self.asset_id
        res = super().unlink()
        assets_before._sync_odometer_meter()
        return res

    def _check_state_transition(self, new_state):
        for log in self:
            if log.state == new_state:
                continue
            if new_state not in STATE_TRANSITIONS.get(log.state, set()):
                raise UserError(
                    self.env._(
                        "%(record)s cannot move from %(current)s to %(target)s. "
                        "Reset it to New first.",
                        record=log.display_name,
                        current=log.state,
                        target=new_state,
                    )
                )

    @api.constrains("odometer")
    def _check_odometer_non_negative(self):
        for log in self:
            if log.odometer < 0:
                raise ValidationError(
                    self.env._(
                        "Odometer reading cannot be negative (got %(value)s).",
                        value=log.odometer,
                    )
                )

    @api.constrains("odometer", "asset_id", "date")
    def _check_odometer_sequence(self):
        dirty = self.filtered("odometer")
        if not dirty:
            return

        by_asset = dirty._get_odometer_timeline()
        for log in dirty:
            previous, next_entry = log._find_odometer_neighbours(by_asset, log.id)
            if previous and log.odometer < previous.odometer:
                raise ValidationError(
                    self.env._(
                        "Odometer (%(current)s) cannot be less than previous reading (%(previous)s) on %(date)s.",
                        current=log.odometer,
                        previous=previous.odometer,
                        date=previous.date,
                    )
                )
            if next_entry and log.odometer > next_entry.odometer:
                raise ValidationError(
                    self.env._(
                        "Odometer (%(current)s) cannot be greater than next reading (%(next)s) on %(date)s.",
                        current=log.odometer,
                        next=next_entry.odometer,
                        date=next_entry.date,
                    )
                )

    def _get_odometer_timeline(self):
        timeline = self.sudo().search_fetch(
            [("asset_id", "in", self.asset_id.ids), ("odometer", ">", 0)],
            ["asset_id", "date", "odometer"],
            order="asset_id, date, id",
        )
        by_asset = {}
        for entry in timeline:
            if entry.date:
                by_asset.setdefault(entry.asset_id.id, []).append(entry)
        return by_asset

    def _find_odometer_neighbours(self, by_asset, skip_id):
        self.check_singleton()
        if not self.date:
            return None, None
        entries = by_asset.get(self.asset_id.id, [])
        dates = [entry.date for entry in entries]
        left = bisect_left(dates, self.date)
        right = bisect_right(dates, self.date)
        previous = next(
            (entry for entry in reversed(entries[:left]) if entry.id != skip_id),
            None,
        )
        next_entry = next(
            (entry for entry in entries[right:] if entry.id != skip_id),
            None,
        )
        return previous, next_entry

    def action_set_done(self):
        self.write({"state": "done"})

    def action_set_cancelled(self):
        self.write({"state": "cancelled"})

    def action_set_new(self):
        self.write({"state": "new"})
