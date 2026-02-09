# -*- coding: utf-8 -*-

def convert_field(cr, model, field, target_model):
    table = model.replace('.', '_')

    cr.execute("""SELECT 1
                    FROM information_schema.columns
                   WHERE table_name = %s
                     AND column_name = %s
                     AND table_schema = current_schema
               """, (table, field))
    if not cr.fetchone():
        return

    cr.execute("SELECT id FROM ir_model_fields WHERE model=%s AND name=%s", (model, field))
    [fields_id] = cr.fetchone()

    cr.execute("""
        INSERT INTO ir_property(name, type, fields_id, company_id, res_id, value_reference)
        SELECT %(field)s, 'many2one', %(fields_id)s, company_id, CONCAT('{model},', id),
               CONCAT('{target_model},', {field})
          FROM {table} t
         WHERE {field} IS NOT NULL
           AND NOT EXISTS(SELECT 1
                            FROM ir_property
                           WHERE fields_id=%(fields_id)s
                             AND company_id=t.company_id
                             AND res_id=CONCAT('{model},', t.id))
    """.format(**locals()), locals())

    cr.execute('ALTER TABLE "{0}" DROP COLUMN "{1}" CASCADE'.format(table, field))

def migrate(cr, version):
    convert_field(cr, 'res.partner', 'property_purchase_currency_id', 'res.currency')
    convert_field(cr, 'product.template',
                  'property_account_creditor_price_difference', 'account.account')
