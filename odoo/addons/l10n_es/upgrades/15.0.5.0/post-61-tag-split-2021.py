# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    # For taxes coming from tax templates, replace grid 61 by the right tag.
    # For the other ones, we can't guess what to use, and the user will have to change his
    # config manually, possibly creating a ticket to ask to fix his accounting history.

    def get_taxes_from_templates(templates):
        cr.execute(f"""
            SELECT array_agg(tax.id)
            FROM account_tax tax
            JOIN ir_model_data data
                ON data.model = 'account.tax'
                AND data.res_id = tax.id
                AND data.module = 'l10n_es'
                AND data.name ~ '^[0-9]*_({'|'.join(templates)})\\Z'
        """)

        return cr.fetchone()[0]
    env = api.Environment(cr, SUPERUSER_ID, {})

    templates_mapping = {
        'mod_303_120': ['account_tax_template_s_iva_ns', 'account_tax_template_s_iva_ns_b'],
        'mod_303_122': ['account_tax_template_s_iva_e', 'account_tax_template_s_iva0_isp'],
    }

    # To run in a server action to fix issues on dbs with custom taxes,
    # replace the content of this dict.
    taxes_mapping = {}
    for tag_name, template_names in templates_mapping.items():
        taxes_from_templates = get_taxes_from_templates(template_names)
        if taxes_from_templates:
            taxes_mapping[tag_name] = taxes_from_templates

    old_tag = env.ref('l10n_es.mod_303_61')
    for tag_name, tax_ids in taxes_mapping.items():
        # Grid 61 is only for base repartition.
        # If it was used for taxes repartition, we don't touch it (and it'll require manual check,
        # as the BOE file probably won't pass government checks).

        new_tag = env.ref(f'l10n_es.{tag_name}')

        # Change tax config
        cr.execute("""
            UPDATE account_account_tag_account_tax_repartition_line_rel tax_rep_tag
            SET account_account_tag_id = %s
            FROM account_account_tag new_tag, account_tax_repartition_line repln
            WHERE tax_rep_tag.account_account_tag_id = %s
            AND repln.id = tax_rep_tag.account_tax_repartition_line_id
            AND COALESCE(repln.invoice_tax_id, repln.refund_tax_id) IN %s
        """, [new_tag.id, old_tag.id, tuple(tax_ids)])

        # Change amls in history, starting at Q3 2021 (date of introduction for the new tags)

        # Set tags
        cr.execute("""
            UPDATE account_account_tag_account_move_line_rel aml_tag
            SET account_account_tag_id = %s
            FROM account_move_line aml, account_move_line_account_tax_rel aml_tax
            WHERE aml_tag.account_move_line_id = aml.id
            AND aml_tax.account_move_line_id = aml.id
            AND aml.date >= '2021-07-01'
            AND aml_tax.account_tax_id IN %s
            AND aml_tag.account_account_tag_id = %s
        """, [new_tag.id, tuple(tax_ids), old_tag.id])

        # Fix tax audit string
        cr.execute("""
            UPDATE account_move_line aml
            SET tax_audit = REPLACE(tax_audit, %s, %s)
            FROM account_account_tag_account_move_line_rel aml_tag
            WHERE aml_tag.account_move_line_id = aml.id
            AND aml_tag.account_account_tag_id = %s
        """, [old_tag.name, f"{new_tag.name}:", new_tag.id])
