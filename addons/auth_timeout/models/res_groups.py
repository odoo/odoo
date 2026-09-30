from odoo import api, fields, models
from odoo.tools import ormcache

CACHE_INVALIDATE_FIELDS = ("lock_timeout", "lock_timeout_mfa", "lock_timeout_inactivity", "lock_timeout_inactivity_mfa")


def human_readable_delay(minutes):
    if not minutes:
        return minutes, "minutes"
    if minutes % 1440 == 0:
        return minutes // 1440, "days"
    elif minutes % 60 == 0:
        return minutes // 60, "hours"
    else:
        return minutes, "minutes"


def human_readable_delay_to_minutes(delay, unit):
    if unit == "days":
        return delay * 1440
    elif unit == "hours":
        return delay * 60
    else:
        return delay


DELAY_UNITS = [
    ("minutes", "minutes"),
    ("hours", "hours"),
    ("days", "days"),
]


class ResGroups(models.Model):
    _inherit = "res.groups"

    lock_timeout = fields.Integer(
        string="Session timeout",
        help="Time interval (in minutes) after which re-authentication is required, regardless of inactivity.",
    )

    lock_timeout_mfa = fields.Boolean(
        string="Require MFA on session timeout",
        help="Enable two-factor authentication when the session timeout is reached.",
    )

    lock_timeout_inactivity = fields.Integer(
        string="Inactivity timeout",
        help="Time (in minutes) of user inactivity after which re-authentication is required.",
    )

    lock_timeout_inactivity_mfa = fields.Boolean(
        string="Require MFA on inactivity timeout",
        help="Enable two-factor authentication when the inactivity timeout is reached.",
    )

    # Technical fields for the user interface
    has_lock_timeout = fields.Boolean(
        help="Requires re-authentication after the user's last connection",
        compute="_compute_has_lock_timeout",
        readonly=False,
    )
    lock_timeout_delay_unit = fields.Selection(DELAY_UNITS, compute="_compute_lock_timeout_delay_unit", readonly=False)
    lock_timeout_delay_in_unit = fields.Integer(compute="_compute_lock_timeout_delay_unit", readonly=False)
    lock_timeout_2fa_selection = fields.Selection(
        [("without_2fa", "Logout"), ("with_2fa", "Logout with two-factor authentication")],
        compute="_compute_lock_timeout_2fa_selection",
        inverse="_inverse_lock_timeout_2fa_selection",
    )

    has_lock_timeout_inactivity = fields.Boolean(
        help="Requires re-authentication after a period of user inactivity",
        compute="_compute_lock_timeout_inactivity_bool",
        readonly=False,
    )
    lock_timeout_inactivity_delay_unit = fields.Selection(
        DELAY_UNITS,
        compute="_compute_lock_timeout_inactivity_delay_unit",
        readonly=False,
    )
    lock_timeout_inactivity_delay_in_unit = fields.Integer(
        compute="_compute_lock_timeout_inactivity_delay_unit",
        readonly=False,
    )
    lock_timeout_inactivity_2fa_selection = fields.Selection(
        [("without_2fa", "Screen lock"), ("with_2fa", "Screen lock with two-factor authentication")],
        compute="_compute_lock_timeout_inactivity_2fa_selection",
        inverse="_inverse_lock_timeout_inactivity_2fa_selection",
    )

    @api.depends("lock_timeout")
    def _compute_has_lock_timeout(self):
        for group in self:
            group.has_lock_timeout = bool(group.lock_timeout)

    @api.depends("lock_timeout")
    def _compute_lock_timeout_delay_unit(self):
        for group in self:
            (
                group.lock_timeout_delay_in_unit,
                group.lock_timeout_delay_unit,
            ) = human_readable_delay(group.lock_timeout)

    @api.depends("lock_timeout_mfa")
    def _compute_lock_timeout_2fa_selection(self):
        for group in self:
            group.lock_timeout_2fa_selection = "with_2fa" if group.lock_timeout_mfa else "without_2fa"

    def _inverse_lock_timeout_2fa_selection(self):
        for group in self:
            group.lock_timeout_mfa = group.lock_timeout_2fa_selection == "with_2fa"

    @api.depends("lock_timeout_inactivity")
    def _compute_lock_timeout_inactivity_bool(self):
        for group in self:
            group.has_lock_timeout_inactivity = bool(group.lock_timeout_inactivity)

    @api.depends("lock_timeout_inactivity")
    def _compute_lock_timeout_inactivity_delay_unit(self):
        for group in self:
            (
                group.lock_timeout_inactivity_delay_in_unit,
                group.lock_timeout_inactivity_delay_unit,
            ) = human_readable_delay(group.lock_timeout_inactivity)

    @api.depends("lock_timeout_inactivity_mfa")
    def _compute_lock_timeout_inactivity_2fa_selection(self):
        for group in self:
            group.lock_timeout_inactivity_2fa_selection = (
                "with_2fa" if group.lock_timeout_inactivity_mfa else "without_2fa"
            )

    def _inverse_lock_timeout_inactivity_2fa_selection(self):
        for group in self:
            group.lock_timeout_inactivity_mfa = group.lock_timeout_inactivity_2fa_selection == "with_2fa"

    @api.onchange("has_lock_timeout")
    def _onchange_has_lock_timeout(self):
        for group in self:
            if not group.has_lock_timeout:
                group.lock_timeout = False
                group.lock_timeout_mfa = False
            else:
                group.lock_timeout = 1440  # 1 day by default
                group.lock_timeout_mfa = True  # Require 2FA by default

    @api.onchange("lock_timeout_delay_unit", "lock_timeout_delay_in_unit")
    def _onchange_lock_timeout_delay_unit(self):
        for group in self:
            group.lock_timeout = human_readable_delay_to_minutes(
                group.lock_timeout_delay_in_unit,
                group.lock_timeout_delay_unit,
            )

    @api.onchange("has_lock_timeout_inactivity")
    def _onchange_has_lock_timeout_inactivity(self):
        for group in self:
            if not group.has_lock_timeout_inactivity:
                group.lock_timeout_inactivity = False
                group.lock_timeout_inactivity_mfa = False
            else:
                group.lock_timeout_inactivity = 15  # 15 minutes by default
                group.lock_timeout_inactivity_mfa = False  # Do not Require 2FA by default

    @api.onchange("lock_timeout_inactivity_delay_unit", "lock_timeout_inactivity_delay_in_unit")
    def _onchange_lock_timeout_inactivity_delay_unit(self):
        for group in self:
            group.lock_timeout_inactivity = human_readable_delay_to_minutes(
                group.lock_timeout_inactivity_delay_in_unit,
                group.lock_timeout_inactivity_delay_unit,
            )

    @api.model_create_multi
    def create(self, vals_list):
        """Override to invalidate `_get_lock_timeouts` cache if timeout fields are set on creation."""
        if any(field in vals for vals in vals_list for field in CACHE_INVALIDATE_FIELDS):
            self.env.registry.clear_cache()
        return super().create(vals_list)

    def write(self, vals):
        """Override to invalidate `_get_lock_timeouts` cache if timeout fields are updated."""
        if any(field in vals for field in CACHE_INVALIDATE_FIELDS):
            self.env.registry.clear_cache()
        return super().write(vals)

    def unlink(self):
        """Override to invalidate `_get_lock_timeouts` cache if timeout fields exist on deleted records."""
        if self.filtered(lambda r: any(r[field] for field in CACHE_INVALIDATE_FIELDS)):
            self.env.registry.clear_cache()
        return super().unlink()

    @ormcache("self._ids")
    def _get_lock_timeouts(self):
        """
        Compute the session and inactivity timeout settings for the user.

        This method returns the shortest configured timeouts (in seconds) across all groups
        implied by the user's group membership. For each type of timeout, it distinguishes
        between those that require MFA and those that do not.

        :return: A dictionary with timeout types as keys and a list of tuples as values.
            Each tuple is of the form (timeout_in_seconds, requires_mfa), ordered from shortest to longest.

            Example::

                {
                    'lock_timeout': [(43200, False), (86400, True)],
                    'lock_timeout_inactivity': [(900, False)]
                }

        :rtype: dict
        """
        result = {}

        for key, mfa_key in [
            ("lock_timeout", "lock_timeout_mfa"),
            ("lock_timeout_inactivity", "lock_timeout_inactivity_mfa"),
        ]:
            # `with_context({})` because
            # - Same reasons than https://github.com/odoo/odoo/commit/7a0255665714f2c0129d04d4a3f14a3137c159f1
            # - As this method is decorated with `@ormcache('self._ids')`, it cannot depend on the context
            values = [(g[key], g[mfa_key]) for g in self.with_context({}).all_implied_ids if g[key]]
            min_non_mfa = min((timeout for timeout, mfa in values if not mfa), default=None)
            min_mfa = min((timeout for timeout, mfa in values if mfa), default=None)

            result[key] = []

            if min_mfa:
                result[key].append((min_mfa * 60, True))
            if min_non_mfa and (not min_mfa or min_non_mfa < min_mfa):
                result[key].append((min_non_mfa * 60, False))

            # Sort from lowest timeout to highest
            result[key].sort()

        return result
