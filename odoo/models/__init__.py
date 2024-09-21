# ruff: noqa: F401
# Exports features of the ORM to developers.
# This is a `__init__.py` file to avoid merge conflicts on `odoo/models.py`.

# TODO we should only expose *Model objects here, maybe check_comp*
from odoo.tools import _

from odoo.orm.commands import Command
from odoo.orm.identifiers import NewId
from odoo.orm.models import (
    GC_UNLINK_LIMIT,
    LOG_ACCESS_COLUMNS,
    MAGIC_COLUMNS,
    READ_GROUP_DISPLAY_FORMAT,
    READ_GROUP_NUMBER_GRANULARITY,
    AbstractModel,
    BaseModel,
    MetaModel,
    Model,
    TransientModel,
    UserError,
    ValidationError,
    check_companies_domain_parent_of,
    check_company_domain_parent_of,
    fix_import_export_id_paths,
    is_definition_class,
    parse_read_group_spec,
    to_company_ids,
)
from odoo.orm.utils import (
    PREFETCH_MAX,
    READ_GROUP_TIME_GRANULARITY,
    check_method_name,
    check_object_name,
    check_pg_name,
    check_property_field_value_name,
    expand_ids,
    regex_object_name,
)
