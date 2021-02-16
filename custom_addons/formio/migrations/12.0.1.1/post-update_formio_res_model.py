# Copyright Nova Code (http://www.novacode.nl)
# See LICENSE file for full licensing details.

def migrate(cr, version):
    update_query = """
    UPDATE formio_builder
    SET res_model_id = NULL
    """
    cr.execute(update_query)
