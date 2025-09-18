# Exports features of the ORM to developers.
# This is a `__init__.py` file to avoid merge conflicts on `odoo/models.py`.

# Constants
from odoo.orm.constants import (
    READ_GROUP_AGGREGATE,
    READ_GROUP_DISPLAY_FORMAT,
    READ_GROUP_NUMBER_GRANULARITY,
    READ_GROUP_TIME_GRANULARITY,
)
from odoo.orm.primitives import LOG_ACCESS_COLUMNS, MAGIC_COLUMNS
from odoo.orm.parsing import regex_order

# Model classes
from odoo.orm.models import (
    AbstractModel,
    BaseModel,
    MetaModel,
    Model,
    TransientModel,
)

# Table objects
from odoo.orm.models.table_objects import Constraint, Index, UniqueIndex

# Registration utilities
from odoo.orm.registration import (
    add_to_registry,
    is_model_class,
    is_model_definition,
)

# Utilities
from odoo.orm.helpers import (
    check_companies_domain_parent_of,
    check_company_domain_parent_of,
    to_record_ids,
)
from odoo.orm.parsing import fix_import_export_id_paths, parse_read_group_spec
from odoo.orm.validation import check_object_name, check_pg_name
