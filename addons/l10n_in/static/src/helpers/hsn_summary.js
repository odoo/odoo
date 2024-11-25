import { patch } from "@web/core/utils/patch";

import { accountTaxHelpers } from "@account/helpers/account_tax";

patch(accountTaxHelpers, {
    /**
     * [!] Mirror of the same method in account_tax.py.
     * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
     */
    l10n_in_get_hsn_summary_table(base_lines, display_uom) {
        const results_map = {};
        const l10n_in_tax_types = new Set();
        for (const base_line of base_lines) {
            const l10n_in_hsn_code = base_line.l10n_in_hsn_code;
            if (!l10n_in_hsn_code) {
                continue;
            }

            const price_unit = base_line.price_unit;
            const discount = base_line.discount;
            const quantity = base_line.quantity;
            const product = base_line.product;
            const uom = base_line.uom || {};
            const taxes = base_line.taxes_data;

            const final_price_unit = price_unit * (1 - discount / 100);

            // Compute the taxes.
            const taxes_computation = this.get_tax_details(taxes, final_price_unit, quantity, {
                precision_rounding: 0.01,
                rounding_method: "round_per_line",
                product: product,
            });

            // Rate.
            const gst_tax_amounts = taxes_computation.taxes_data
                .filter((x) => ["igst", "cgst", "sgst"].includes(x.tax.l10n_in_tax_type))
                .map((x) => [x.tax.id, x.tax.amount]);
            const unique_gst_tax_amounts = Array.from(new Set(gst_tax_amounts.map(JSON.stringify)))
                .map(JSON.parse);
            let rate = 0;
            for (const [, tax_amount] of unique_gst_tax_amounts) {
                rate += tax_amount;
            }

            const key = {
                l10n_in_hsn_code: l10n_in_hsn_code,
                rate: rate,
                uom_name: uom.name || "",
            };
            const keyStr = JSON.stringify(key);

            if (keyStr in results_map) {
                results_map[keyStr].quantity += quantity;
                results_map[keyStr].amount_untaxed += taxes_computation.total_excluded;
            } else {
                results_map[keyStr] = {
                    ...key,
                    quantity: quantity,
                    amount_untaxed: taxes_computation.total_excluded,
                    tax_amounts: {
                        igst: 0.0,
                        cgst: 0.0,
                        sgst: 0.0,
                        cess: 0.0,
                    },
                };
            }

            for (const tax_data of taxes_computation.taxes_data) {
                if (tax_data.tax.l10n_in_tax_type) {
                    results_map[keyStr].tax_amounts[tax_data.tax.l10n_in_tax_type] += tax_data.tax_amount;
                    l10n_in_tax_types.add(tax_data.tax.l10n_in_tax_type);
                }
            }
        }

        const items = [];
        for (const value of Object.values(results_map)) {
            items.push({
                l10n_in_hsn_code: value.l10n_in_hsn_code,
                uom_name: value.uom_name,
                rate: value.rate,
                quantity: value.quantity,
                amount_untaxed: value.amount_untaxed,
                tax_amount_igst: value.tax_amounts.igst,
                tax_amount_cgst: value.tax_amounts.cgst,
                tax_amount_sgst: value.tax_amounts.sgst,
                tax_amount_cess: value.tax_amounts.cess,
            });
        }
        return {
            has_igst: l10n_in_tax_types.has("igst"),
            has_gst: l10n_in_tax_types.has("cgst") || l10n_in_tax_types.has("sgst"),
            has_cess: l10n_in_tax_types.has("cess"),
            nb_columns: 5 + l10n_in_tax_types.size,
            display_uom: display_uom,
            items: items,
        };
    },
});
