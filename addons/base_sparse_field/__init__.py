# -*- coding: utf-8 -*-

from . import models
from . import tests

def _update_database_schema(cr):
    # The reflection of fields is done before updating the model's schema,
    # therefore we first update the schema.
    cr.execute("""
        ALTER TABLE ir_model_fields
        ADD COLUMN serialization_field_id integer REFERENCES ir_model_fields ON DELETE cascade
    """)
