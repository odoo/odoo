# Part of Odoo. See LICENSE file for full copyright and licensing details.


def migrate(cr, version):
    # income_tax_id becomes a computed field synced with the SK_TIN additional
    # identifier. Seed the identifier from the existing values beforehand, so
    # they survive the recomputation of the field.
    cr.execute("""
        UPDATE res_partner p
           SET additional_identifiers = COALESCE(p.additional_identifiers, '{}'::jsonb)
               || jsonb_build_object('SK_TIN', c.income_tax_id)
          FROM res_company c
         WHERE c.partner_id = p.id
           AND c.income_tax_id IS NOT NULL
           AND c.income_tax_id != ''
           AND NOT COALESCE(p.additional_identifiers, '{}'::jsonb) ? 'SK_TIN'
    """)
