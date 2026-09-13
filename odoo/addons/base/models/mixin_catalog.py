from odoo import fields, models

SOURCE_LANG = "en_US"

assert SOURCE_LANG.replace("_", "").isalnum(), "SOURCE_LANG must be an alphanumeric tag"
_NAME_SOURCE_SQL = f"(name->>'{SOURCE_LANG}')"


def name_uniq_index(*scope, message=None, nulls_distinct=False, where=None):
    columns = ", ".join([_NAME_SOURCE_SQL, *scope])
    nulls = "" if nulls_distinct else " NULLS NOT DISTINCT"
    predicate = f" WHERE {where}" if where else ""
    return models.UniqueIndex(
        f"({columns}){nulls}{predicate}",
        message or "A record with this name already exists in this catalog.",
    )


def no_name_uniq_index():
    return models.UniqueIndex(lambda registry: "")


class MixinCatalog(models.AbstractModel):
    _name = "mixin.catalog"
    _description = "Catalog Entry (unique translated name, archivable)"

    name = fields.Char(
        translate=True,
        required=True,
    )
    active = fields.Boolean(default=True)

    _name_src_uniq = name_uniq_index()
