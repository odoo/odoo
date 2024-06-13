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
    const evalContext = accountTaxHelpers.eval_taxes_computation_prepare_context(
        priceUnit,
        quantity,
        accountTaxHelpers.eval_taxes_computation_prepare_product_values(
            productDefaultValues,
            product
        ),
        {
            rounding_method: company.tax_calculation_rounding_method,
            precision_rounding: currency.rounding,
        }
    );
    return accountTaxHelpers.computeSingleLineTaxes(taxes, evalContext);
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
