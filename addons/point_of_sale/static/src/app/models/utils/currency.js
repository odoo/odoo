import { formatMonetary } from "@web/fields/formatters";
export const formatCurrency = (value, currency, hasSymbol = true) =>
    formatMonetary(value, {
        currencyId: currency.id,
        noSymbol: !hasSymbol,
    });

export const roundCurrency = (value, currency) => currency.round(value);
