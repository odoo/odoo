from typing import Literal, Self

from odoo import api, fields, models, tools
from odoo.api import ValuesType
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MailMessageSubtype(models.Model):
    _name = "mail.message.subtype"
    _description = "Message subtypes"
    _order = "sequence, id"

    name = fields.Char(
        string="Message Type",
        translate=True,
        required=True,
        help="Precise message type, mostly for system notifications (e.g. New, "
        "Stage change). Lets users fine-tune which notifications they receive.",
    )
    description = fields.Text(
        translate=True,
        prefetch=True,
        help="Description that will be added in the message posted for this "
        "subtype. If void, the name will be added instead.",
    )
    internal = fields.Boolean(
        string="Internal Only",
        help="Messages with internal subtypes will be visible only by employees, aka members of base_user group",
    )
    parent_id: MailMessageSubtype = fields.Many2one(
        comodel_name="mail.message.subtype",
        ondelete="set null",
        help="Parent subtype, used for automatic subscription (e.g. a project "
        "subtype's parent_id points to the related task subtype).",
    )
    relation_field = fields.Char(
        string="Relation field",
        help="Field used to link the related model to the subtype model when "
        "using automatic subscription on a related document. The field "
        "is used to compute getattr(related_document.relation_field).",
    )
    res_model = fields.Char(
        string="Model",
        help="Model the subtype applies to. If False, this subtype applies to all models.",
    )
    default = fields.Boolean(
        default=True,
        help="Activated by default when subscribing.",
    )
    sequence = fields.Integer(
        default=1,
        help="Used to order subtypes.",
    )
    hidden = fields.Boolean(help="Hide the subtype in the follower options")
    track_recipients = fields.Boolean(
        help="Whether to display all the recipients or only the important ones."
    )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        _debug.lifecycle("create", count=len(vals_list), cache="mail")
        self.env.registry.clear_cache("mail")
        return super().create(vals_list)

    def write(self, vals: ValuesType) -> Literal[True]:
        _debug.lifecycle("write", subtypes=self.ids, fields=list(vals), cache="mail")
        self.env.registry.clear_cache("mail")
        return super().write(vals)

    def unlink(self) -> Literal[True]:
        _debug.lifecycle("unlink", subtypes=self.ids, cache="mail")
        self.env.registry.clear_cache("mail")
        return super().unlink()

    @tools.ormcache("model_name", cache="mail")
    def _get_auto_subscription_subtypes(self, model_name: str) -> tuple:
        child_ids, def_ids = [], []
        all_int_ids = []
        parent, relation = {}, {}
        subtypes = self.sudo().search(
            [
                "|",
                "|",
                ("res_model", "=", False),
                ("res_model", "=", model_name),
                ("parent_id.res_model", "=", model_name),
            ]
        )
        for subtype in subtypes:
            if not subtype.res_model or subtype.res_model == model_name:
                child_ids += subtype.ids
                if subtype.default:
                    def_ids += subtype.ids
            if subtype.relation_field:
                parent[subtype.id] = subtype.parent_id.id
                relation.setdefault(subtype.res_model, set()).add(
                    subtype.relation_field
                )
            if subtype.internal:
                all_int_ids += subtype.ids
        _debug.perf.count(
            "auto_subscription_subtypes_computed",
            model=model_name,
            subtypes=len(subtypes),
            defaults=len(def_ids),
            relations=len(relation),
        )
        return child_ids, def_ids, all_int_ids, parent, relation

    @api.model
    def default_subtypes(self, model_name: str) -> tuple:
        subtype_ids, internal_ids, external_ids = self._get_subtypes(model_name)
        return (
            self.browse(subtype_ids),
            self.browse(internal_ids),
            self.browse(external_ids),
        )

    @tools.ormcache("self.env.su", "self.env.user.share", "model_name", cache="mail")
    def _get_subtypes(self, model_name: str) -> tuple:
        domain = [
            ("default", "=", True),
            "|",
            ("res_model", "=", model_name),
            ("res_model", "=", False),
        ]
        subtypes = (
            self.sudo() if not self.env.su and self.env.user.share else self
        ).search(domain)
        internal = subtypes.filtered("internal")
        _debug.perf.count(
            "default_subtypes_computed",
            model=model_name,
            subtypes=len(subtypes),
            internal=len(internal),
        )
        return subtypes.ids, internal.ids, (subtypes - internal).ids
