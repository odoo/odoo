/** @odoo-module */
import {
    eval_taxes_computation,
    eval_taxes_computation_prepare_context,
    prepare_taxes_computation,
} from "@account/helpers/account_tax";

// -------------------------------------------------------------------------
// HELPERS IN BOTH PYTHON/JAVASCRIPT (account_tax.js / account_tax.py)

// PREPARE TAXES COMPUTATION
// -------------------------------------------------------------------------

/**
 * [!] Mirror of the same method in account_tax.py.
 * PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
*/
export function l10n_in_get_hsn_summary_table(base_lines, display_uom){
    const results_map = {}
    const l10n_in_tax_types = new Set();
    for(const base_line of base_lines){
        const l10n_in_hsn_code = base_line.l10n_in_hsn_code;
        if(!l10n_in_hsn_code){
            continue;
        }

        const price_unit = base_line.price_unit;
        const quantity = base_line.quantity;
        const product = base_line.product;
        let uom = base_line.uom;
        const tax_values_list = base_line.taxes;

        // Compute the taxes.
        const eval_context = eval_taxes_computation_prepare_context(price_unit, quantity, {
            product: product,
            rounding_method: "round_per_line",
            precision_rounding: 0.01,
        });
        const taxes_computation = eval_taxes_computation(
            prepare_taxes_computation(tax_values_list, eval_context),
            eval_context,
        );

        // Rate.
        const gst_tax_amounts = taxes_computation.tax_values_list
            .filter(x => ['igst', 'cgst', 'sgst'].includes(x._l10n_in_tax_type))
            .map(x => [x.id, x.amount]);
        let rate = 0;
        for(const [, tax_amount] of gst_tax_amounts){
            rate += tax_amount;
        }

        const key = {
            l10n_in_hsn_code: l10n_in_hsn_code,
            rate: rate,
            uom: uom,
        };
        const keyStr = JSON.stringify(key);

        if(results_map.hasOwnProperty(keyStr)){
            results_map[keyStr].quantity += quantity;
            results_map[keyStr].amount_untaxed += taxes_computation.total_excluded;
        }else{
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

        for(const tax_values of taxes_computation.tax_values_list){
            if(tax_values._l10n_in_tax_type){
                results_map[keyStr].tax_amounts[tax_values._l10n_in_tax_type] += tax_values.tax_amount_factorized;
                l10n_in_tax_types.add(tax_values._l10n_in_tax_type);
            }
        }
    }

    const items = [];
    for(const value of Object.values(results_map)){
        items.push({
            l10n_in_hsn_code: value.l10n_in_hsn_code,
            uom: value.uom,
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
        has_igst: l10n_in_tax_types.has('igst'),
        has_gst: l10n_in_tax_types.has('cgst') || l10n_in_tax_types.has('sgst'),
        has_cess: l10n_in_tax_types.has('cess'),
        nb_columns: 5 + l10n_in_tax_types.size,
        display_uom: display_uom,
        items: items,
    }
}
