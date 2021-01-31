# Copyright Nova Code (http://www.novacode.nl)
# See LICENSE file for full licensing details.

def migrate(cr, version):
    update_query = """
    UPDATE formio_form
    SET portal_share = formio_builder.portal, public_share = formio_builder.public
    FROM formio_builder
    WHERE formio_form.builder_id = formio_builder.id
    """
    cr.execute(update_query)
