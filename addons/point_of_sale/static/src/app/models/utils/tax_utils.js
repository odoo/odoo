/** @odoo-module */

import { accountTaxHelpers } from "@account/helpers/account_tax";

export const getPriceUnitAfterFiscalPosition = (
    taxes,
    priceUnit,
    product,
    productDefaultValues,
    fiscalPosition,
    models
) => {
    if (!fiscalPosition) {
        return priceUnit;
    }

    const newTaxes = getTaxesAfterFiscalPosition(taxes, fiscalPosition, models);
    return accountTaxHelpers.adapt_price_unit_to_another_taxes(
        priceUnit,
        accountTaxHelpers.eval_taxes_computation_prepare_product_values(
            productDefaultValues,
            product
        ),
        taxes,
        newTaxes
    );
};

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
        if (fiscalPosition._tax_mapping_by_ids[tax.id]) {
            for (const mapTaxId of fiscalPosition._tax_mapping_by_ids[tax.id]) {
                newTaxIds.push(mapTaxId);
            }
        } else {
            newTaxIds.push(tax.id);
        }
    }

    return models["account.tax"].filter((tax) => newTaxIds.includes(tax.id));
};
