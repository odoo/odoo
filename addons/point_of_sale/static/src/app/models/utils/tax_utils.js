import { accountTaxHelpers } from "@account/helpers/account_tax";

/**
 * This method will return a new price so that if you apply the taxes the price will remain the same
 * For example if the original price is 50. It will compute a new price so that if you apply the tax_ids
 * the price would still be 50.
 */
export const compute_price_force_price_include = (
    tax_ids,
    price,
    product,
    product_default_values,
    company,
    currency,
    models
) => {
    const tax_res = getTaxesValues(
        tax_ids,
        price,
        1,
        product,
        product_default_values,
        company,
        currency,
        "total_included"
    );
    let new_price = tax_res.total_excluded;
    new_price += tax_res.taxes_data
        .filter((tax) => models["account.tax"].get(tax.id).price_include)
        .reduce((sum, tax) => (sum += tax.tax_amount), 0);
    return new_price;
};

export const getTaxesValues = (
    taxes,
    priceUnit,
    quantity,
    product,
    productDefaultValues,
    company,
    currency,
    special_mode = null
) => {
    const baseLine = accountTaxHelpers.prepare_base_line_for_taxes_computation(
        {},
        {
            product_id: accountTaxHelpers.eval_taxes_computation_prepare_product_values(
                productDefaultValues,
                product
            ),
            tax_ids: taxes,
            price_unit: priceUnit,
            quantity: quantity,
            currency_id: currency,
            special_mode: special_mode,
        }
    );
    accountTaxHelpers.add_tax_details_in_base_line(baseLine, company);
    accountTaxHelpers.round_base_lines_tax_details([baseLine], company);

    const results = baseLine.tax_details;
    for (const taxData of results.taxes_data) {
        Object.assign(taxData, taxData.tax);
    }
    return results;
};

export const getTaxesAfterFiscalPosition = (taxes, fiscalPosition, models) => {
    if (!fiscalPosition) {
        return taxes;
    }

    const newTaxIds = [];
    for (const tax of taxes) {
        if (fiscalPosition.tax_map[tax.id]) {
            for (const mapTaxId of fiscalPosition.tax_map[tax.id]) {
                newTaxIds.push(mapTaxId);
            }
        } else {
            newTaxIds.push(tax.id);
        }
    }

    return models["account.tax"].filter((tax) => newTaxIds.includes(tax.id));
};
