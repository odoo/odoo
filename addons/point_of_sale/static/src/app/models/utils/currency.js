import { formatMonetary } from "@web/views/fields/formatters";
import { roundDecimals, roundPrecision } from "@web/core/utils/numbers";

export const formatCurrency = (value, currency, hasSymbol = true) => {
    return formatMonetary(value, {
        currencyId: currency.id,
        noSymbol: !hasSymbol,
    });
};

export const roundCurrency = (value, currency) => {
    return roundDecimals(value, currency.decimal_places);
};

export const getCurrencyRounding = (owner) => {
    if (owner?.currency?.rounding) {
        return owner.currency.rounding;
    }
    if (owner?.pos?.currency?.rounding) {
        return owner.pos.currency.rounding;
    }
    return 0.01;
};

export const roundOwnerCurrency = (amount, owner) => {
    const v = roundPrecision(amount, getCurrencyRounding(owner));
    return v === 0 ? 0 : v;
};
