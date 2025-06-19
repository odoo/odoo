import { patch } from "@web/core/utils/patch";

import { accountTaxHelpers } from "@account/helpers/account_tax";

patch(accountTaxHelpers, {
    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    l10n_in_get_hsn_summary_table(base_lines, display_uom) {
        const l10n_in_tax_types = new Set();
        const items_map = {};

        function get_base_line_grouping_key(base_line) {
            const unique_taxes_data = new Set(
                base_line.tax_details.taxes_data
                    .filter(tax_data => ['igst', 'cgst', 'sgst'].includes(tax_data.tax.l10n_in_tax_type))
                    .map(tax_data => tax_data.tax)
            );
            const rate = [...unique_taxes_data].reduce((sum, tax) => sum + tax.amount, 0);

            return {
                l10n_in_hsn_code: base_line.l10n_in_hsn_code,
                uom_name: base_line.product_uom_id.name,
                rate: rate,
            };
        }

        // quantity / amount_untaxed.
        for (const base_line of base_lines) {
            const raw_key = get_base_line_grouping_key(base_line);
            if (!raw_key.l10n_in_hsn_code) {
                continue;
            }

            const key = JSON.stringify(raw_key);
            if (!(key in items_map)) {
                items_map[key] = {
                    key: raw_key,
                    quantity: 0.0,
                    amount_untaxed: 0.0,
                    tax_amount_igst: 0.0,
                    tax_amount_cgst: 0.0,
                    tax_amount_sgst: 0.0,
                    tax_amount_cess: 0.0,
                }
            }

            const item = items_map[key];
            item.quantity += base_line.quantity;
            item.amount_untaxed += (
                base_line.tax_details.total_excluded_currency +
                base_line.tax_details.delta_total_excluded_currency
            );
        }

        // Tax amounts.
        function grouping_function(base_line, tax_data) {
            return tax_data ? {
                ...get_base_line_grouping_key(base_line),
                l10n_in_tax_type: tax_data.tax.l10n_in_tax_type,
            } : null;
        }

        const base_lines_aggregated_values = this.aggregate_base_lines_tax_details(base_lines, grouping_function);
        const values_per_grouping_key = this.aggregate_base_lines_aggregated_values(base_lines_aggregated_values);
        for (const values of Object.values(values_per_grouping_key)) {
            const grouping_key = values.grouping_key;
            if (!grouping_key || !grouping_key.l10n_in_hsn_code || !grouping_key.l10n_in_tax_type) {
                continue;
            }

            const key = JSON.stringify({
                l10n_in_hsn_code: grouping_key.l10n_in_hsn_code,
                uom_name: grouping_key.uom_name,
                rate: grouping_key.rate,
            });
            const item = items_map[key];
            const l10n_in_tax_type = grouping_key.l10n_in_tax_type;
            item[`tax_amount_${l10n_in_tax_type}`] += values.tax_amount_currency;
            l10n_in_tax_types.add(l10n_in_tax_type);
        }

        const items = [];
        for (const values of Object.values(items_map)) {
            const item = {...values.key, ...values};
            delete item.key;
            items.push(item);
        }
        return {
            has_igst: l10n_in_tax_types.has("igst"),
            has_gst: l10n_in_tax_types.has("cgst") || l10n_in_tax_types.has("sgst"),
            has_cess: l10n_in_tax_types.has("cess"),
            nb_columns: 5 + l10n_in_tax_types.size,
            display_uom: display_uom,
            items: items,
        };
    }
});
