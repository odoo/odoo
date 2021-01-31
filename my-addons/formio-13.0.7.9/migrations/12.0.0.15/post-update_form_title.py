# Copyright Nova Code (http://www.novacode.nl)
# See LICENSE file for full licensing details.

def migrate(cr, version):
    update_query = """
    UPDATE formio_form
    SET title = (SELECT b.title FROM formio_builder AS b WHERE b.id = builder_id)
    """
    cr.execute(update_query)
