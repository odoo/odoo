# ruff: noqa: F401
# Exports features of the ORM to developers.
# This is a `__init__.py` file to avoid merge conflicts on `odoo/models.py`.

# TODO we should only expose *Model objects, TableObjects, maybe check_comp*

from odoo.orm.models import (
    LOG_ACCESS_COLUMNS,
    MAGIC_COLUMNS,
    READ_GROUP_DISPLAY_FORMAT,
    READ_GROUP_NUMBER_GRANULARITY,
    AbstractModel,
    BaseModel,
    MetaModel,
    Model,
    check_companies_domain_parent_of,
    check_company_domain_parent_of,
    fix_import_export_id_paths,
    parse_read_group_spec,
    regex_order,
    to_record_ids,
)
from odoo.orm.model_classes import is_model_class, is_model_definition
from odoo.orm.models_transient import TransientModel
from odoo.orm.table_objects import Constraint, Index, UniqueIndex
from odoo.orm.utils import (
    READ_GROUP_TIME_GRANULARITY,
    check_method_name,
    check_object_name,
    check_pg_name,
)
