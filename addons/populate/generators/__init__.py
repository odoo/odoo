# ruff: noqa: RUF067
import logging

from .binary import (
    Binary,
    Image,
)
from .choice import (
    Sample,
    Selection,
)
from .generator import (
    DEFAULT_GENERATORS,
    Generator,
    PopulateGeneratorError,
    UniqueValueNotFound,
    UnmetDependencies,
    get_fields_vals,
)
from .misc import (
    Counter,
    Cycle,
    Eval,
)
from .properties import (
    PropertyDefinition,
    PropertyProp,
    PropertyValue,
)
from .reference import (
    ReferenceOne,
    ReferenceRaw,
)
from .relation import (
    RelationMany,
    RelationOne,
)
from .scalar import (
    Boolean,
    Float,
    Integer,
    Monetary,
)
from .temporal import (
    Date,
    Datetime,
)
from .textual import (
    Char,
    Text,
)

_logger = logging.getLogger(__name__)

# Auto-discover and register all allowed Faker generators at loading time
try:
    from faker import Faker

    from . import fake

    faker = Faker()

    for method_name in dir(faker):
        if fake.is_allowed(faker, method_name):
            fake.KNOWN_METHODS.add(method_name)
            fake.create(method_name)

except ImportError:
    _logger.info("Faker library isn't installed, skipping creation of 'fake.*' generators. "
                 "Won't be able to run blueprints that use them. "
                 "Install it from odoo/addons/populate/requirements.txt")
    faker = None
