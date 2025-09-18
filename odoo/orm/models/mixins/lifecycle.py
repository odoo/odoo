"""
Lifecycle operations mixin for BaseModel.

This module contains methods for model lifecycle management:
- External ID operations (get_external_id, _get_external_ids)
- Archive/Unarchive operations (action_archive, action_unarchive)
- Registration hooks (_register_hook, _unregister_hook)
- Onchange support (_has_onchange, _apply_onchange_methods, onchange)
- Model identity helpers (is_transient)
- URL/access helpers (_get_redirect_suggested_company, _can_return_content)
- Placeholder support (_get_placeholder_filename)
"""

import typing
from collections import defaultdict

from odoo.tools.translate import _

from ... import decorators as api
from ..._typing import DomainType, IdType

if typing.TYPE_CHECKING:
    from collections.abc import Collection

    from ...fields.base import Field


class LifecycleMixin:
    """Mixin providing lifecycle and metadata operations for recordsets.

    This mixin contains methods for:
    - External ID operations
    - Archive/Unarchive operations
    - Registration hooks
    - Onchange support
    - Model identity helpers
    - URL/access helpers
    """

    __slots__ = ()

    def _get_external_ids(self) -> dict[IdType, list[str]]:
        """Retrieve the External ID(s) of any database record.

        **Synopsis**: ``_get_external_ids() -> { 'id': ['module.external_id'] }``

        :return: map of ids to the list of their fully qualified External IDs
                 in the form ``module.key``, or an empty list when there's no External
                 ID for a record, e.g.::

                     { 'id': ['module.ext_id', 'module.ext_id_bis'],
                       'id2': [] }
        """
        result = defaultdict(list)
        domain: DomainType = [
            ("model", "=", self._name),
            ("res_id", "in", self.ids),
        ]
        for data in (
            self.env["ir.model.data"]
            .sudo()
            .search_read(domain, ["module", "name", "res_id"], order="id")
        ):
            result[data["res_id"]].append(f"{data['module']}.{data['name']}")
        return {record.id: result[record._origin.id] for record in self}

    def get_external_id(self) -> dict[IdType, str]:
        """Retrieve the External ID of any database record, if there
        is one. This method works as a possible implementation
        for a function field, to be able to add it to any
        model object easily, referencing it as ``Model.get_external_id``.

        When multiple External IDs exist for a record, only one
        of them is returned (randomly).

        :return: map of ids to their fully qualified XML ID,
                 defaulting to an empty string when there's none
                 (to be usable as a function field),
                 e.g.::

                     { 'id': 'module.ext_id',
                       'id2': '' }
        """
        results = self._get_external_ids()
        return {key: val[0] if val else "" for key, val in results.items()}

    @classmethod
    def is_transient(cls) -> bool:
        """Return whether the model is transient.

        See :class:`TransientModel`.

        """
        return cls._transient

    @api.deprecated("Deprecated since 19.0, use action_archive or action_unarchive")
    def toggle_active(self) -> None:
        "Inverses the value of :attr:`active` on the records in ``self``."
        assert self._active_name, f"No 'active' field on model {self._name}"
        active_recs = self.filtered(self._active_name)
        active_recs.action_archive()
        (self - active_recs).action_unarchive()

    def action_archive(self) -> None:
        """Set :attr:`active` to ``False`` on a recordset for active records.

        Note, you probably want to override `write()` method if you want to take
        action once the active field changes.
        """
        field_name = self._active_name
        assert field_name, f"No 'active' field on model {self._name}"
        active_recs = self.filtered(lambda record: record[field_name])
        active_recs[field_name] = False

    def action_unarchive(self) -> None:
        """Set :attr:`active` to ``True`` on a recordset for inactive records.

        Note, you probably want to override `write()` method if you want to take
        action once the active field changes.
        """
        field_name = self._active_name
        assert field_name, f"No 'active' field on model {self._name}"
        inactive_recs = self.filtered(lambda record: not record[field_name])
        inactive_recs[field_name] = True

    def _register_hook(self) -> None:
        """stuff to do right after the registry is built"""

    def _unregister_hook(self) -> None:
        """Clean up what `~._register_hook` has done."""

    def _get_redirect_suggested_company(self) -> typing.Any:
        """Return the suggested company to be set on the context
        in case of a URL redirection to the record. To avoid multi
        company issues when clicking on a shared link, this
        could be called to try setting the most suited company on
        the allowed_company_ids in the context. This method can be
        overridden, for example on the hr.leave model, where the
        most suited company is the company of the leave type, as
        specified by the ir.rule.
        """
        if "company_id" in self:
            return self.company_id
        elif "company_ids" in self:
            return (self.company_ids & self.env.user.company_ids)[:1]
        return False

    def _can_return_content(
        self, field_name: str | None = None, access_token: str | None = None
    ) -> bool:
        """Determine whether one can export a file or an image from a field of
        record ``self``, even if ``self`` is not accessible to the current user.
        If so, the record will be ``sudo()``-ed to access the corresponding file
        or image.

        :param field_name: image field name to check the access to
        :param access_token: access token to use instead of the
            access rights and access rules
        :return: whether the extra access is allowed
        """
        self.ensure_one()
        return False

    #
    # Generic onchange method
    #

    def _has_onchange(self, field: Field, other_fields: Collection[Field]) -> bool:
        """Return whether ``field`` should trigger an onchange event in the
        presence of ``other_fields``.
        """
        return (field.name in self._onchange_methods) or any(
            dep in other_fields
            for dep in self.pool.get_dependent_fields(field.base_field)
        )

    def _apply_onchange_methods(self, field_name: str, result: dict) -> None:
        """Apply onchange method(s) for field ``field_name`` on ``self``. Value
        assignments are applied on ``self``, while warning messages are put
        in dictionary ``result``.
        """
        for method in self._onchange_methods.get(field_name, ()):
            res = method(self)
            if not res:
                continue
            if res.get("value"):
                for key, val in res["value"].items():
                    if key in self._fields and key != "id":
                        self[key] = val
            if res.get("warning"):
                result["warnings"].add(
                    (
                        res["warning"].get("title") or _("Warning"),
                        res["warning"].get("message") or "",
                        res["warning"].get("type") or "",
                    )
                )

    def onchange(self, values: dict, field_names: list[str], fields_spec: dict) -> dict:
        raise NotImplementedError("onchange() is implemented in module 'web'")

    def _get_placeholder_filename(self, field: str) -> str | bool:
        """Returns the filename of the placeholder to use,
        set on web/static/img by default, or the
        complete path to access it (eg: module/path/to/image.png).
        """
        return False
