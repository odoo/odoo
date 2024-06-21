import { accountTaxHelpers } from "@account/helpers/account_tax";

export const getTaxesValues = (
    taxes,
    priceUnit,
    quantity,
    product,
    productDefaultValues,
    company,
    currency
) => {
    const results = accountTaxHelpers.evaluate_taxes_computation(taxes, priceUnit, quantity, {
        precision_rounding: currency.rounding,
        rounding_method: company.tax_calculation_rounding_method,
        product: accountTaxHelpers.eval_taxes_computation_prepare_product_values(
            productDefaultValues,
            product
        ),
    });
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
