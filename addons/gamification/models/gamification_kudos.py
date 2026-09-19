from typing import Any, Literal, Self

from markupsafe import Markup, escape

from odoo import _, api, exceptions, fields, models
from odoo.models import ValuesType


class GamificationKudosCategory(models.Model):
    """Category for peer recognition kudos (e.g. Teamwork, Innovation, Quality)."""

    _name = "gamification.kudos.category"
    _description = "Kudos Category"
    _order = "sequence, name"

    name = fields.Char(
        string="Category",
        translate=True,
        required=True,
    )
    description = fields.Text(translate=True)
    sequence = fields.Integer(default=10)
    icon = fields.Char(
        string="Icon CSS Class",
        default="fa fa-thumbs-up",
        help="Font Awesome icon class, e.g. 'fa fa-star', 'fa fa-heart'.",
    )
    color = fields.Integer(
        string="Color Index",
        default=0,
    )
    karma_granted = fields.Integer(
        string="Karma Bonus",
        default=5,
        help="Karma automatically granted to the recipient when kudos is sent.",
    )
    active = fields.Boolean(default=True)
    kudos_ids = fields.One2many(
        comodel_name="gamification.kudos",
        inverse_name="category_id",
    )
    # The hand-rolled compute this replaces carried no @api.depends at all, so
    # the ORM cached its result for the whole transaction and nothing ever marked
    # it dirty: the count was simply wrong from the first kudos onwards.  The
    # category had no inverse one2many, which is why it hand-rolled a _read_group
    # in the first place; declaring the relation makes the counter one line and
    # its invalidation the ORM's problem.
    kudos_count = fields.Count(
        count_of="kudos_ids",
        string="# Kudos",
    )


# Fields whose value the sender picked at send-time (or that were derived
# from that choice) and that the activity feed / the mail-thread post were
# computed from. Editing them after create() does not re-run any of that:
# summary re-renders (it is a stored @api.depends compute, and
# _compute_summary depends on sender_id.name same as the other three) but
# the activity feed / the posted message keep their original values, so they
# would silently disagree. karma_granted is included even though it is not a
# sender-picked input: it is derived from category_id at create() time and
# is otherwise a plain readonly=True Integer -- UI-only, not ORM-enforced --
# so leaving it out of this set let the sender rewrite the kudos' own record
# of how much karma it granted, with no trace, via write()/RPC/sudo.
KUDOS_VALUE_FIELDS = frozenset(
    {"sender_id", "recipient_id", "category_id", "message", "karma_granted"}
)


# Kudos are lightweight, informal recognition acts. Unlike badges (which
# have granting rules and scarcity), any employee can send kudos to any
# other employee at any time. Kudos integrate with mixin.mail.thread so they
# appear in the Discuss social feed.
class GamificationKudos(models.Model):
    """Peer-to-peer recognition message."""

    _name = "gamification.kudos"
    _description = "Peer Recognition"
    _inherit = ["mixin.mail.thread"]
    _order = "create_date desc"
    _rec_name = "summary"
    _mail_partner_fields = ("recipient_partner_id",)

    sender_id = fields.Many2one(
        comodel_name="res.users",
        string="From",
        default=lambda self: self.env.uid,
        index=True,
        readonly=True,
        required=True,
        ondelete="cascade",
    )
    sender_partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="sender_id.partner_id",
        string="Sender Partner",
    )
    recipient_id = fields.Many2one(
        comodel_name="res.users",
        string="To",
        index=True,
        required=True,
        ondelete="cascade",
    )
    recipient_partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="recipient_id.partner_id",
        string="Recipient Partner",
    )
    category_id = fields.Many2one(
        comodel_name="gamification.kudos.category",
        required=True,
        ondelete="restrict",
    )
    message = fields.Text(required=True)
    summary = fields.Char(
        compute="_compute_summary",
        precompute=True,
        store=True,
    )
    karma_granted = fields.Integer(
        readonly=True,
        help="Karma points granted to the recipient.",
    )

    @api.depends("sender_id.name", "recipient_id.name", "category_id.name")
    def _compute_summary(self) -> None:
        """Generate a one-line summary for display."""
        for kudos in self:
            kudos.summary = _(
                "%(sender)s recognized %(recipient)s for %(category)s",
                sender=kudos.sender_id.name or "",
                recipient=kudos.recipient_id.name or "",
                category=kudos.category_id.name or "",
            )

    def write(self, vals: ValuesType) -> Literal[True]:
        """Freeze the fields that already drove karma/summary/the mail post.

        Only ``create()`` grants karma and posts to the thread; editing
        ``sender_id``/``recipient_id``/``category_id``/``message`` afterwards
        would re-render ``summary`` (a stored compute) without touching
        ``karma_granted`` or the already-sent post, leaving the three
        disagreeing about what was actually recognized. ``sudo()`` (imports,
        migrations) still bypasses this, same as ``create()``'s sender check.

        The ``kudos_user_write`` record rule already blocks anyone but the
        sender from writing at all, so a non-sender's attempt must keep
        raising the ORM's own ``AccessError`` via ``super().write()`` below
        -- this only adds a stricter rule for the one path the record rule
        *does* allow: the sender editing their own already-sent kudos.
        """
        if (
            not self.env.su
            and KUDOS_VALUE_FIELDS.intersection(vals)
            and any(kudos.sender_id == self.env.user for kudos in self)
        ):
            raise exceptions.UserError(
                _("A sent kudos cannot be edited; send a new one instead.")
            )
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        """Validate and create kudos, granting karma and posting notifications."""
        for vals in vals_list:
            # A non-system caller can only send kudos *as themselves*. Reject a
            # foreign ``sender_id`` loudly instead of silently rewriting it:
            # the old coercion handed the caller back a record different from
            # the one they asked for, with no visible error.
            if not self.env.su:
                # Missing/falsy sender_id (imports, legacy RPC) is "no
                # opinion", not a spoof — only a present, different id is
                # rejected.
                sender_id = vals.get("sender_id")
                if sender_id and sender_id != self.env.uid:
                    raise exceptions.UserError(
                        _("Kudos can only be sent in your own name.")
                    )
                vals["sender_id"] = self.env.uid
            if vals.get("sender_id", self.env.uid) == vals.get("recipient_id"):
                raise exceptions.UserError(_("You cannot send kudos to yourself."))

        records = super().create(vals_list)

        # Batched: the caller may legitimately send many kudos at once (an
        # import, a team-wide thank-you), and the per-record loop this replaces
        # cost a karma write cycle, a message_post and a feed insert each.
        karma_per_user: dict[Any, dict[str, Any]] = {}
        for kudos in records:
            karma = kudos.category_id.karma_granted
            if not karma:
                continue
            entry = karma_per_user.setdefault(
                kudos.recipient_id,
                {
                    "gain": 0,
                    "source": kudos.sender_id,
                    "reason": _("Kudos: %s", kudos.category_id.name),
                },
            )
            entry["gain"] += karma
            # sudo(): karma_granted is now in KUDOS_VALUE_FIELDS, and write()
            # blocks the sender from touching it -- but sender_id is always
            # the current user right after a non-su create(), so this
            # create-time bookkeeping write must bypass that guard the same
            # way create()'s own sender check is bypassed by sudo().
            kudos.sudo().karma_granted = karma
        if karma_per_user:
            self.env["res.users"].sudo()._add_karma_batch(karma_per_user)

        for kudos in records:
            # Post to mail thread for social visibility
            # Use Markup so HTML tags render; %-formatting auto-escapes str values
            body = Markup(
                '<i class="%s"/> <b>%s</b> recognized <b>%s</b> for <em>%s</em>: %s'
            ) % (
                escape(kudos.category_id.icon or ""),
                kudos.sender_id.name,
                kudos.recipient_id.name,
                kudos.category_id.name,
                kudos.message,
            )
            kudos.message_post(
                body=body,
                partner_ids=[kudos.recipient_partner_id.id],
                subtype_xmlid="mail.mt_comment",
                email_layout_xmlid="mail.mail_notification_light",
            )

        self.env["gamification.activity"]._log_batch(
            [
                {
                    "activity_type": "kudos",
                    "user_id": kudos.sender_id.id,
                    "target_user_id": kudos.recipient_id.id,
                    "icon": kudos.category_id.icon or "fa fa-heart",
                    "karma_gained": kudos.karma_granted,
                    "summary_args": {"category": kudos.category_id.name},
                }
                for kudos in records
            ]
        )

        return records
