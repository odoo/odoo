from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "data_recycle_model", ["res_model_name"])
    schema.drop_columns(cr, "data_recycle_record", ["res_model_id", "res_model_name"])
