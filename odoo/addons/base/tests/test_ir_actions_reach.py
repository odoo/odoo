from lxml import etree

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestIrActionsReach(TransactionCase):
    """Every button and menu that can reach an action admits only users the
    action admits, so `_get_load_refusal` never refuses a user the interface
    invited. Read off the installed registry: the set grows with the modules
    installed, and a row here is fixed on the trigger or on the action."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Groups = cls.env["res.groups"].sudo()
        cls.implied = {
            group.id: set(group.all_implied_ids.ids) for group in cls.Groups.search([])
        }
        cls.internal = cls.env.ref("base.group_user").id
        cls.external = {
            cls.env.ref("base.group_portal").id,
            cls.env.ref("base.group_public").id,
        }
        cls.actions = cls._actions_with_groups()

    @classmethod
    def _actions_with_groups(cls):
        found = {}
        for model_name in cls.env["ir.actions.actions"]._get_model_names_in_tree():
            Model = cls.env[model_name].sudo()
            if "group_ids" not in Model._fields:
                continue
            for action in Model.search_fetch(
                [("group_ids", "!=", False)], ["group_ids"]
            ):
                found[action.id] = (model_name, set(action.group_ids.ids))
        return found

    def _group_ids(self, attr):
        ids = set()
        for token in (attr or "").split(","):
            token = token.strip().lstrip("!")
            if token:
                gid = self.env["ir.model.data"]._xmlid_to_res_id(
                    token, raise_if_not_found=False
                )
                if gid:
                    ids.add(gid)
        return ids

    def _internal_only(self, group_ids):
        return {g for g in group_ids if not (self.implied.get(g, {g}) & self.external)}

    def _uncovered(self, viewer_groups, action_groups):
        viewers = self._internal_only(viewer_groups) or {self.internal}
        return sorted(
            g for g in viewers if not (self.implied.get(g, {g}) & action_groups)
        )

    def _readers_of(self, model):
        if model not in self.env or self.env[model]._transient:
            return set()
        rules = (
            self.env["ir.model.access"]
            .sudo()
            .search([("model_id.model", "=", model), ("perm_read", "=", True)])
        )
        if any(not rule.group_id for rule in rules):
            return set()
        return {rule.group_id.id for rule in rules}

    def _action_id(self, name):
        try:
            return int(name)
        except ValueError:
            if "." in name:
                return self.env["ir.model.data"]._xmlid_to_res_id(
                    name, raise_if_not_found=False
                )
        return 0

    def _button_gaps(self):
        gaps = []
        Views = self.env["ir.ui.view"].sudo().with_context(active_test=False)
        for view in Views.search_fetch(
            [("arch_db", "ilike", 'type="action"')], ["model", "group_ids", "arch_db"]
        ):
            try:
                root = etree.fromstring(view.arch_db.encode())
            except etree.XMLSyntaxError:
                continue
            for node in root.iter("button", "a"):
                if node.get("type") != "action":
                    continue
                action = self.actions.get(self._action_id(node.get("name") or ""))
                if not action:
                    continue
                viewers = set(view.group_ids.ids) | self._group_ids(node.get("groups"))
                for ancestor in node.iterancestors():
                    viewers |= self._group_ids(ancestor.get("groups"))
                if not viewers:
                    viewers = self._readers_of(view.model)
                if uncovered := self._uncovered(viewers, action[1]):
                    gaps.append(
                        (
                            f"view {view.id} ({view.model})",
                            node.get("name"),
                            action,
                            uncovered,
                        )
                    )
        return gaps

    def _menu_gaps(self):
        gaps = []
        Menus = self.env["ir.ui.menu"].sudo().with_context(active_test=False)
        for menu in Menus.search_fetch(
            [("action", "!=", False)], ["action", "complete_name"]
        ):
            action = self.actions.get(menu.action.id if menu.action else 0)
            if not action:
                continue
            holder = menu
            while holder and not holder.group_ids:
                holder = holder.parent_id
            viewers = set(holder.group_ids.ids) if holder else set()
            if uncovered := self._uncovered(viewers, action[1]):
                gaps.append(
                    (f"menu {menu.complete_name}", menu.action.id, action, uncovered)
                )
        return gaps

    def _describe(self, gaps):
        return "\n".join(
            f"{trigger} -> {name} {model} (id {action_id}): reachable by "
            f"{', '.join(self.Groups.browse(uncovered).mapped('full_name'))}"
            for trigger, name, (model, _groups), uncovered in gaps
            for action_id in [self._action_id(str(name))]
        )

    def test_every_button_admits_only_users_its_action_admits(self):
        if described := self._describe(self._button_gaps()):
            self.fail(described)

    def test_every_menu_admits_only_users_its_action_admits(self):
        if described := self._describe(self._menu_gaps()):
            self.fail(described)
