import { formatMonetary } from "@web/views/fields/formatters";

export const formatCurrency = (value, currency, hasSymbol = true) =>
    formatMonetary(value, {
        currencyId: currency.id,
        noSymbol: !hasSymbol,
    });

export const roundCurrency = (value, currency) => currency.round(value);

export const taxKey = (taxIds) =>
    taxIds
        .map((tax) => tax.id)
        .sort((a, b) => a - b)
        .join("_");
