from odoo import SUPERUSER_ID, api
from odoo.db.schema import column_exists

COLUMNS = (
    "documents_product_settings",
    "product_folder_id",
)


def migrate(cr, version):
    if not version:
        return
    present = [column for column in COLUMNS if column_exists(cr, "res_company", column)]
    if not present:
        return
    # the rows through the ORM, so every default and required value is
    # applied; the values by SQL, straight from the company's columns
    env = api.Environment(cr, SUPERUSER_ID, {})
    companies = env["res.company"].with_context(active_test=False).search([])
    env["document_product.config"]._for_each(companies)
    env.flush_all()
    assignments = ", ".join(f"{column} = c.{column}" for column in present)
    cr.execute(
        f"UPDATE document_product_config x SET {assignments} FROM res_company c WHERE c.id = x.company_id"
    )
    _move_product_tags(env)
    env.invalidate_all()


def _move_product_tags(env):
    """The many2many rows, from the company's relation table to the
    configuration's.

    The company side named its table `product_tags_table` explicitly; the
    configuration lets the ORM derive one, so the names are read off the field
    rather than written down twice.
    """
    field = env["document_product.config"]._fields["product_tag_ids"]
    cr = env.cr
    cr.execute("SELECT to_regclass('product_tags_table')")
    if not cr.fetchone()[0]:
        return
    cr.execute(
        f"""
        INSERT INTO {field.relation} ({field.column1}, {field.column2})
             SELECT config.id, old.document_tag_id
               FROM product_tags_table old
               JOIN document_product_config config
                 ON config.company_id = old.res_company_id
        ON CONFLICT DO NOTHING
        """
    )
