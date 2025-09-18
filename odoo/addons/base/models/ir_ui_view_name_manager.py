import collections
import functools
import logging
from typing import Any

from lxml import etree
from markupsafe import Markup

from odoo.tools import _, frozendict

_logger = logging.getLogger(__name__)


class NameManager:
    """An object that manages all the named elements in a view."""

    def __init__(
        self,
        model: Any,
        parent: NameManager | None = None,
        model_groups: Any = None,
    ) -> None:
        self.model = model
        self.env = model.env  # for dynamically-resolved translations
        self.available_fields = collections.defaultdict(
            dict
        )  # {field_name: {'groups': groups, 'info': field_info}}
        self.available_actions = set()
        self.available_names = set()
        self.used_fields = collections.defaultdict(
            dict
        )  # {field_name: {'groups': '(use, node)}}
        self.used_names = {}  # {name: use}
        self.must_exist_actions = {}
        self.must_exist_groups = {}
        self.parent = parent
        self.children = []
        if self.parent:
            self.parent.children.append(self)

        # group_definitions is the factory for making group expression objects
        self.group_definitions = self.model.env["res.groups"]._get_group_definitions()

        # this represents the group of users that have access to this model
        self.model_groups = (
            self.group_definitions.universe if model_groups is None else model_groups
        )

        # this maps field names to the group of users that have access to the field
        self.field_groups = {}

    @functools.cached_property
    def field_info(self) -> dict[str, Any]:
        field_info = self.model.fields_get(attributes=["readonly", "required"])
        if not (self.model.has_access("write") or self.model.has_access("create")):
            for info in field_info.values():
                info["readonly"] = True
        return field_info

    def has_field(
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

    def has_action(self, name: str) -> None:
        self.available_actions.add(name)

    def must_have_fields(
        self,
        node: etree._Element,
        names: set[str],
        node_info: dict[str, Any],
        use: str,
    ) -> None:
        access_groups = node_info["model_groups"] & node_info["view_groups"]
        for name in names:
            if name == "id":
                continue
            if not name.startswith("parent."):
                self.used_fields[name][access_groups] = (use, node)
            elif self.parent:
                self.parent.must_have_fields(node, {name[7:]}, node_info, use)

    def must_have_name(self, name: str, use: str) -> None:
        self.used_names[name] = use

    def must_exist_action(self, action_id: str, node: etree._Element) -> None:
        self.must_exist_actions[action_id] = node

    def must_exist_group(self, name: str, node: etree._Element) -> None:
        self.must_exist_groups[name] = node

    def _get_field_groups(self, name: str) -> Any:
        """Return the group expression representing the users having read access to the field."""
        if name in self.field_groups:
            return self.field_groups[name]

        access_groups = self.model_groups

        field = self.model._fields.get(name)
        if (
            not field
            and name not in self.available_names
            and name not in self.field_info
        ):
            access_groups = self.group_definitions.empty
        elif field and field.groups:
            access_groups &= self.group_definitions.parse(
                field.groups, raise_if_not_found=False
            )

        self.field_groups[name] = access_groups
        return access_groups

    def check(self, view: Any) -> None:
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
                view._raise_view_error(msg)
            if name not in self.available_actions and name not in self.available_names:
                msg = _(
                    "Name or id \u201c%(name_or_id)s\u201d in %(use)s must be present in view but is missing.",
                    name_or_id=name,
                    use=use,
                )
                view._raise_view_error(msg)

        for name in self.available_fields:
            if name not in self.model._fields and name not in self.field_info:
                message = _("Field `%(name)s` does not exist", name=name)
                view._raise_view_error(message)

        for name, node in self.must_exist_actions.items():
            # logic mimics /web/action/load behaviour
            action = False
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
                    view._raise_view_error(msg, node)
                if not issubclass(view.pool[model], view.pool["ir.actions.actions"]):
                    msg = _(
                        "%(xmlid)s is of type %(xmlid_model)s, expected a subclass of ir.actions.actions",
                        xmlid=name,
                        xmlid_model=model,
                    )
                    view._raise_view_error(msg, node)
            action = view.env["ir.actions.actions"].browse(action_id).exists()
            if not action:
                msg = _(
                    "Action %(action_reference)s (id: %(action_id)s) does not exist for button of type action.",
                    action_reference=name,
                    action_id=action_id,
                )
                view._raise_view_error(msg, node)

        for name, node in self.must_exist_groups.items():
            if self.group_definitions.get_id(name) is None:
                msg = _(
                    "The group \u201c%(name)s\u201d defined in view does not exist!",
                    name=name,
                )
                view._log_view_warning(msg, node)

        for name, groups_uses in self.used_fields.items():
            use, node = next(iter(groups_uses.values()))
            if name == "id":  # always available
                continue
            if "." in name:
                msg = _(
                    "Invalid composed field %(definition)s in %(use)s",
                    definition=name,
                    use=use,
                )
                view._raise_view_error(msg)
            info = self.available_fields[name].get("info")

            if info is None:
                if name in ["false", "true"]:
                    _logger.warning(
                        "Using Javascript syntax 'true, 'false' in expressions is deprecated, found %s",
                        name,
                    )
                    continue
            elif (
                info.get("select") == "multi"
            ):  # mainly for searchpanel, but can be a generic behaviour.
                msg = _(
                    "Field \u201c%(name)s\u201d used in %(use)s is present in view but is in select multi.",
                    name=name,
                    use=use,
                )
                view._raise_view_error(msg)

        for name, (
            missing_groups,
            reasons,
        ) in self.get_missing_fields().items():
            message, error_type = self._error_message_group_inconsistency(
                name, missing_groups, reasons
            )
            if error_type == "does_not_exist":
                view._raise_view_error(message)
            elif error_type:
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

    def update_available_fields(self) -> None:
        for name, info in self.available_fields.items():
            info.update(self.field_info.get(name, ()))

    def get_missing_fields(self) -> dict[str, tuple[Any, list[tuple]]]:
        """
        return {'field_name': (missing_groups | False, [mandatory_groups, use, node])}
        """
        # model has read access for group E and F
        # field_a has a (python) group G
        # <div groups="A,B">
        #   <field name="field_a" invisible="field_b" groups="A,C"/>
        #   <field name="field_a" groups="B"/>
        #   <field name="field_c" required="field_a" groups="B1"/>
        #   <field name="field_c" required="field_a" groups="B2"/>
        # </div>
        #

        # views have many elements with the same groups
        parent = self
        while parent.parent:
            parent = parent.parent

        missing_fields = {}
        for name, groups_uses in self.used_fields.items():
            errors = []
            used = []

            for used_groups, (use, node) in groups_uses.items():
                available_info = self.available_fields.get(name, {})
                # Access is restricted to the administrator only. There is no need to check
                # groups as they are not used.
                if used_groups.is_empty():
                    if not available_info.get("groups", []):
                        used.append((used_groups, use, node))
                    continue

                # No match possible using only access right and groups on the field.
                if not (used_groups <= self._get_field_groups(name)):
                    errors.append((used_groups, use, node))
                    continue

                # At least one field in view match match with the used combinations.
                available_combined_groups = self.group_definitions.empty
                nodes_groups = available_info.get("groups", [])
                for groups in nodes_groups:
                    available_combined_groups |= groups

                if not (used_groups <= available_combined_groups):
                    used.append((used_groups, use, node))

            if errors:
                missing_fields[name] = (False, errors)
                continue

            if not used:
                continue

            missing_groups = self.group_definitions.empty
            for groups, _use, _node in used:
                missing_groups |= groups

            missing_fields[name] = (missing_groups, used)

        return missing_fields
