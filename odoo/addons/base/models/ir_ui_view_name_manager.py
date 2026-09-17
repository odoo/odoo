import collections
import functools
import logging
from typing import Any

from lxml import etree
from markupsafe import Markup

from odoo.libs.debug_log import DebugLog
from odoo.tools import _, frozendict

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class NameManager:
    def __init__(
        self,
        model: Any,
        parent: NameManager | None = None,
        model_groups: Any = None,
        group_definitions: Any = None,
    ) -> None:
        self.model = model
        self.env = model.env
        self.available_fields = collections.defaultdict(dict)
        self.available_actions = set()
        self.available_names = set()
        self.used_fields = collections.defaultdict(dict)
        self.used_names = {}
        self.required_actions = {}
        self.required_groups = {}
        self.parent = parent
        self.children = []
        if self.parent:
            self.parent.children.append(self)
        _debug.lifecycle(
            "name_manager.created",
            model=model._name,
            nested=parent is not None,
            scoped_groups=model_groups is not None,
        )

        if group_definitions is None:
            group_definitions = self.model.env["res.groups"]._get_group_definitions()
        self.group_definitions = group_definitions

        self.model_groups = (
            self.group_definitions.universe if model_groups is None else model_groups
        )

        self.field_groups = {}

        self.warning: Markup = Markup("")

    @functools.cached_property
    def field_info(self) -> dict[str, Any]:
        info = self.model.fields_get(attributes=())
        _debug.perf.count("field_info_loaded", model=self.model._name, fields=len(info))
        return info

    def add_available_field(
        self,
        node: etree._Element,
        name: str,
        node_info: dict[str, Any],
        info: dict[str, Any] = frozendict(),
    ) -> None:
        self.available_fields[name].setdefault("info", {}).update(info)
        self.field_groups[name] = node_info["model_groups"]
        self.available_fields[name].setdefault("groups", []).append(
            node_info["view_groups"]
        )
        self.available_names.add(info.get("id") or name)

    def add_available_action(self, name: str) -> None:
        self.available_actions.add(name)

    @staticmethod
    def _describe_use(use: tuple[str, str]) -> str:
        attr, expr = use
        return f"{attr}={expr!r}"

    def add_used_fields(
        self,
        node: etree._Element,
        names: set[str],
        node_info: dict[str, Any],
        use: tuple[str, str],
    ) -> None:
        access_groups = node_info["model_groups"] & node_info["view_groups"]
        for name in sorted(names):
            if name == "id":
                continue
            if not name.startswith("parent."):
                self.used_fields[name][access_groups] = (use, node)
            elif self.parent:
                _debug.logic(
                    "used_field.delegated_to_parent",
                    model=self.model._name,
                    field=name[7:],
                    attribute=use[0],
                )
                self.parent.add_used_fields(node, {name[7:]}, node_info, use)

    def add_used_name(self, name: str, use: str) -> None:
        self.used_names[name] = use

    def add_required_action(self, action_id: str, node: etree._Element) -> None:
        self.required_actions[action_id] = node

    def add_required_group(self, name: str, node: etree._Element) -> None:
        self.required_groups[name] = node

    def _get_field_groups(self, name: str) -> Any:
        if name in self.field_groups:
            return self.field_groups[name]

        access_groups = self.model_groups

        field = self.model._fields.get(name)
        if (
            not field
            and name not in self.available_names
            and name not in self.field_info
        ):
            _debug.logic(
                "field_groups.unknown_field", model=self.model._name, field=name
            )
            access_groups = self.group_definitions.empty
        elif field and field.groups:
            access_groups &= self.group_definitions.parse(
                field.groups, raise_if_not_found=False
            )

        self.field_groups[name] = access_groups
        return access_groups

    def check(self, view: Any) -> None:
        _debug.pipeline(
            "name_manager_check",
            view=view.id,
            model=self.model._name,
            used_names=len(self.used_names),
            available_fields=len(self.available_fields),
            children=len(self.children),
        )
        self._check_used_names(view)
        self._check_available_fields(view)
        self._check_required_actions(view)
        self._check_required_groups(view)
        self._check_used_fields(view)
        self._check_group_consistency(view)

    def _check_used_names(self, view: Any) -> None:
        for name, use in self.used_names.items():
            if (
                name not in self.available_actions
                and name not in self.available_names
                and name not in self.model._fields
                and name not in self.field_info
            ):
                msg = _(
                    "Name or id \u201c%(name_or_id)s\u201d in %(use)s does not exist.",
                    name_or_id=name,
                    use=use,
                )
                _debug.logic(
                    "name_check_failed", view=view.id, name=name, reason="unknown"
                )
                raise view._prepare_view_error(msg)
            if name not in self.available_actions and name not in self.available_names:
                msg = _(
                    "Name or id \u201c%(name_or_id)s\u201d in %(use)s must be present in view but is missing.",
                    name_or_id=name,
                    use=use,
                )
                _debug.logic(
                    "name_check_failed", view=view.id, name=name, reason="not_in_view"
                )
                raise view._prepare_view_error(msg)

    def _check_available_fields(self, view: Any) -> None:
        for name in self.available_fields:
            if name not in self.model._fields and name not in self.field_info:
                message = _("Field `%(name)s` does not exist", name=name)
                _debug.logic(
                    "name_check_failed", view=view.id, name=name, reason="no_field"
                )
                raise view._prepare_view_error(message)

    def _check_required_actions(self, view: Any) -> None:
        # resolve every reference first, then one existence query for all
        resolved: dict[str, tuple[int, etree._Element]] = {}
        for name, node in self.required_actions.items():
            try:
                action_id = int(name)
            except ValueError:
                model, action_id = view.env["ir.model.data"]._xmlid_to_res_model_res_id(
                    name, raise_if_not_found=False
                )
                if not action_id:
                    msg = _(
                        "Invalid xmlid %(xmlid)s for button of type action.",
                        xmlid=name,
                    )
                    _debug.logic(
                        "action_check_failed",
                        view=view.id,
                        action=name,
                        reason="bad_xmlid",
                    )
                    raise view._prepare_view_error(msg, node) from None
                if not issubclass(view.pool[model], view.pool["ir.actions.actions"]):
                    _debug.logic(
                        "action_check_failed",
                        view=view.id,
                        action=name,
                        model=model,
                        reason="not_an_action",
                    )
                    msg = _(
                        "%(xmlid)s is of type %(xmlid_model)s, expected a subclass of ir.actions.actions",
                        xmlid=name,
                        xmlid_model=model,
                    )
                    raise view._prepare_view_error(msg, node) from None
            resolved[name] = (action_id, node)
        if not resolved:
            return
        existing = set(
            view.env["ir.actions.actions"]
            .browse(list({action_id for action_id, _node in resolved.values()}))
            .exists()
            .ids
        )
        _debug.perf.count(
            "actions_checked",
            view=view.id,
            actions=len(resolved),
            existing=len(existing),
        )
        for name, (action_id, node) in resolved.items():
            if action_id not in existing:
                msg = _(
                    "Action %(action_reference)s (id: %(action_id)s) does not exist for button of type action.",
                    action_reference=name,
                    action_id=action_id,
                )
                _debug.logic(
                    "action_check_failed", view=view.id, action=name, reason="missing"
                )
                raise view._prepare_view_error(msg, node)

    def _check_required_groups(self, view: Any) -> None:
        for name, node in self.required_groups.items():
            if self.group_definitions.get_id(name) is None:
                msg = _(
                    "The group \u201c%(name)s\u201d defined in view does not exist!",
                    name=name,
                )
                _debug.logic("group_unknown", view=view.id, group=name)
                view._log_view_warning(msg, node)

    def _check_used_fields(self, view: Any) -> None:
        for name, groups_uses in self.used_fields.items():
            use, node = next(iter(groups_uses.values()))
            if "." in name:
                _debug.logic(
                    "used_field_refused",
                    view=view.id,
                    field=name,
                    reason="composed",
                )
                msg = _(
                    "Invalid composed field %(definition)s in %(use)s",
                    definition=name,
                    use=self._describe_use(use),
                )
                raise view._prepare_view_error(msg, node)
            # a used name the view has no field for is _check_group_consistency's
            if name in ("false", "true") and name not in self.available_fields:
                _debug.logic("used_field.js_literal", view=view.id, name=name)
                _logger.warning(
                    "Using Javascript syntax 'true, 'false' in expressions is deprecated, found %s",
                    name,
                )

    def _check_group_consistency(self, view: Any) -> None:
        for name, (
            missing_groups,
            reasons,
        ) in self.get_fields_missing().items():
            message, error_type = self._error_message_group_inconsistency(
                name, missing_groups, reasons
            )
            if not error_type:
                continue
            _debug.logic(
                "group_inconsistency",
                view=view.id,
                field=name,
                error_type=error_type,
                reasons=len(reasons),
            )
            if error_type == "does_not_exist":
                raise view._prepare_view_error(message)
            view._log_view_warning(message, None)

    def _error_message_group_inconsistency(
        self, name: str, missing_groups: Any, reasons: list[tuple]
    ) -> tuple[Markup | None, str | None]:
        does_not_exist = (
            name not in self.model._fields and name not in self.available_names
        )
        if not (does_not_exist or missing_groups is False):
            return None, None

        elements = [
            (
                f'<field name="{node.get("name")}"/>'
                if node.tag == "field"
                else f"<{node.tag}>"
            )
            for _item_groups, _use, node in reasons
        ]

        debug = self._prepare_inconsistency_debug(name, does_not_exist, reasons)

        message = Markup("<b>{header}</b><br/>{body}<br/>{footer}<br/>{debug}").format(
            header=_("Access Rights Inconsistency"),
            body=_(
                "This view may not work for all users: some users may have a "
                "combination of groups where the elements %(elements)s are displayed, "
                "but they depend on the field %(field)s that is not accessible. "
                "You might fix this by modifying user groups to make sure that all users "
                "who have access to those elements also have access to the field, "
                "typically via group implications. Alternatively, you could "
                "adjust the \u201c%(groups)s\u201d or \u201c%(invisible)s\u201d attributes for these fields, "
                "to make sure they are always available together.",
                elements=Markup(", ").join(
                    Markup("<b><tt>%s</tt></b>") % element for element in elements
                ),
                field=Markup("<b><tt>%s</tt></b>") % name,
                groups=Markup("<i>groups</i>"),
                invisible=Markup("<i>invisible</i>"),
            ),
            footer=_("Debugging information:"),
            debug=Markup("<br/>").join(debug),
        )

        return message, "does_not_exist" if does_not_exist else "inconsistency"

    def _prepare_inconsistency_debug(
        self, name: str, does_not_exist: bool, reasons: list[tuple]
    ) -> list[str]:
        debug = []
        if does_not_exist:
            debug.append(
                _(
                    "- field \u201c%(name)s\u201d does not exist in model \u201c%(model)s\u201d.",
                    name=name,
                    model=self.model._name,
                )
            )
        else:
            field_groups = self._get_field_groups(name)
            debug.append(
                _(
                    "- field \u201c%(name)s\u201d is accessible for groups: %(field_groups)s",
                    name=name,
                    field_groups=(
                        _("Only super user has access")
                        if field_groups.is_empty()
                        else field_groups
                    ),
                )
            )

        for item_groups, _use, node in reasons:
            clone = etree.Element(node.tag, node.attrib)
            clone.attrib.pop("__validate__", None)
            clone.attrib.pop("__groups_key__", None)
            debug.append(
                _(
                    "- element \u201c%(node)s\u201d is shown in the view for groups: %(groups)s",
                    node=etree.tostring(clone, encoding="unicode"),
                    groups=(
                        _("Free access")
                        if item_groups.is_universal()
                        else (
                            _("Accessible only for the super user")
                            if item_groups.is_empty()
                            else item_groups
                        )
                    ),
                )
            )
        return debug

    def update_available_fields(self) -> None:
        for name, info in self.available_fields.items():
            info.update(self.field_info.get(name, {}))
        _debug.pipeline(
            "available_fields_updated",
            model=self.model._name,
            fields=len(self.available_fields),
        )

    def get_fields_missing(self) -> dict[str, tuple[Any, list[tuple]]]:

        missing_fields = {}
        for name, groups_uses in self.used_fields.items():
            errors = []
            used = []

            for used_groups, (use, node) in groups_uses.items():
                available_info = self.available_fields.get(name, {})
                if used_groups.is_empty():
                    if not available_info.get("groups", []):
                        used.append((used_groups, use, node))
                    continue

                if not (used_groups <= self._get_field_groups(name)):
                    errors.append((used_groups, use, node))
                    continue

                available_combined_groups = self.group_definitions.empty
                nodes_groups = available_info.get("groups", [])
                for groups in nodes_groups:
                    available_combined_groups |= groups

                if not (used_groups <= available_combined_groups):
                    used.append((used_groups, use, node))

            if errors:
                _debug.logic(
                    "field_missing.access_error",
                    model=self.model._name,
                    field=name,
                    uses=len(errors),
                )
                missing_fields[name] = (False, errors)
                continue

            if not used:
                continue

            missing_groups = self.group_definitions.empty
            for groups, _use, _node in used:
                missing_groups |= groups

            missing_fields[name] = (missing_groups, used)

        _debug.perf.count(
            "fields_missing_computed",
            model=self.model._name,
            used_fields=len(self.used_fields),
            missing=len(missing_fields),
        )
        return missing_fields
