# Copyright Nova Code (http://www.novacode.nl)
# See LICENSE file for full licensing details.

def migrate(cr, version):
    update_query = """
    UPDATE formio_form
    SET res_model_id = formio_builder.res_model_id
    FROM formio_builder
    WHERE formio_form.builder_id = formio_builder.id
    """
    cr.execute(update_query)

    update_query = """
    UPDATE formio_form
    SET initial_res_id = res_id
    """
    cr.execute(update_query)
