import typing

from odoo import fields
from odoo.fields import Domain
from odoo.tools.misc import SENTINEL, Sentinel

if typing.TYPE_CHECKING:
    from odoo.models import BaseModel

NEGATIVE_OPERATORS = {
    "!=": "=",
    "not in": "in",
    "not like": "like",
    "not ilike": "ilike",
}


class AssetIdentifier(fields.Char):
    """One identifier of an asset as a column: the value of the identifier
    row whose type carries `identifier_code`. Declared on an asset model, or
    on any model that reaches one through `through` (a many2one name); the
    row is what is stored, and the column is read and written through it.
    """

    identifier_code: str = ""
    through: str = ""

    def __init__(
        self,
        identifier_code: str | Sentinel = SENTINEL,
        through: str | Sentinel = SENTINEL,
        string: str | Sentinel = SENTINEL,
        **kwargs: typing.Any,
    ) -> None:
        super().__init__(
            identifier_code=identifier_code,
            through=through,
            string=string,
            compute=self._compute_identifier,
            inverse=self._inverse_identifier,
            search=self._search_identifier,
            **kwargs,
        )

    def _get_attrs(self, model_class, name: str) -> dict[str, typing.Any]:
        attrs = super()._get_attrs(model_class, name)
        if attrs.get("inherited"):
            return attrs
        # Defaults belong here, not in __init__: a model inheriting the field
        # re-instantiates it with no arguments, and a default written by
        # __init__ would then override what the declaring model said.
        attrs.setdefault("store", True)
        attrs.setdefault("readonly", False)
        attrs.setdefault("copy", False)
        code = attrs.get("identifier_code") or self.identifier_code
        if not code:
            raise TypeError(
                f"Field {model_class._name}.{name}: AssetIdentifier requires "
                "identifier_code."
            )
        through = attrs.get("through") or self.through or ""
        prefix = f"{through}." if through else ""
        attrs.setdefault(
            "_depends",
            (f"{prefix}identifier_ids.value", f"{prefix}identifier_ids.type_id"),
        )
        if attrs.get("store"):
            # A stored column is searched as a column.
            attrs["search"] = None
        return attrs

    def _get_asset(self, record: BaseModel) -> BaseModel:
        return record[self.through] if self.through else record

    def _compute_identifier(self, records: BaseModel) -> None:
        for record in records:
            asset = self._get_asset(record)
            record[self.name] = (
                asset.sudo().get_identifier(self.identifier_code) if asset else False
            )

    def _inverse_identifier(self, records: BaseModel) -> None:
        # The row belongs to the asset; whoever may write this record may
        # name the thing it is, so the row is written as the system.
        for record in records:
            asset = self._get_asset(record)
            if asset:
                asset.sudo()._set_identifier(self.identifier_code, record[self.name])

    def _search_identifier(self, records: BaseModel, operator: str, value):
        prefix = f"{self.through}." if self.through else ""
        typed = Domain("type_id.code", "=", self.identifier_code)
        positive = NEGATIVE_OPERATORS.get(operator, operator)
        if operator in ("=", "!=") and not value:
            domain = Domain(f"{prefix}identifier_ids", "any", typed)
            return domain if operator == "!=" else ~domain
        domain = Domain(
            f"{prefix}identifier_ids", "any", typed & Domain("value", positive, value)
        )
        return ~domain if positive != operator else domain
