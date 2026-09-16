from odoo import _lt, api, models
from odoo.libs.debug_log import DebugLog

from odoo.addons.base.models.mixin_catalog import name_uniq_index

_debug = DebugLog(__name__)


class MixinTagNested(models.AbstractModel):
    _name = "mixin.tag.nested"
    _inherit = ["mixin.tag", "mixin.hierarchy"]
    _description = "Nested Tag (tag with a parent/child hierarchy)"

    _hierarchy_cycle_message = _lt("You can not create recursive tags.")

    _name_src_uniq = name_uniq_index(
        "parent_id",
        message="A tag with this name already exists under the same parent.",
    )

    @api.depends("name", "parent_id.name")
    def _compute_display_name(self):
        paths = {}
        ancestor_ids = set()
        for tag in self:
            if tag.parent_path:
                paths[tag.id] = ids = [
                    int(key) for key in tag.parent_path.split("/") if key
                ]
                ancestor_ids.update(ids)
        ancestors = self.browse(ancestor_ids)
        ancestors.fetch(["name"])
        names = {tag.id: tag.name or "" for tag in ancestors}
        _debug.perf.count(
            "nested_display_names",
            model=self._name,
            tags=len(self),
            with_path=len(paths),
            ancestors=len(ancestors),
        )

        for tag in self:
            path_ids = paths.get(tag.id)
            if path_ids is not None:
                tag.display_name = " / ".join(names[key] for key in path_ids)
                continue
            _debug.logic(
                "nested_display_name_walked",
                model=self._name,
                tag=tag.id,
                reason="no_parent_path",
            )
            walked = []
            seen = set()
            current = tag
            while current and current.id not in seen:
                seen.add(current.id)
                walked.append(current.name or "")
                current = current.parent_id
            tag.display_name = " / ".join(reversed(walked))

    @api.model
    def _search_display_name(self, operator, value):
        domain = super()._search_display_name(operator, value)
        if operator.endswith("like"):
            if operator.startswith("not"):
                _debug.logic(
                    "display_name_search_unsupported",
                    model=self._name,
                    operator=operator,
                )
                return NotImplemented
            _debug.logic(
                "display_name_search_child_of", model=self._name, operator=operator
            )
            return [("id", "child_of", tuple(self._search(domain)))]
        return domain
