/** @odoo-module */

import { formatMonetary, formatFloat } from "@web/views/fields/formatters";
import { roundDecimals } from "@web/core/utils/numbers";
import { registry } from "@web/core/registry";

/**
 * This service introduces `utils` namespace in the `env` which can contain
 * functions that are parameterized by the data in `pos` service.
 */
export const contextualUtilsService = {
    dependencies: ["pos"],
    start(env, { pos }) {
        const currency = pos.currency;
        const productUoMDecimals = pos.dp["Product Unit of Measure"];

        const formatProductQty = (qty) => {
            return formatFloat(qty, { digits: [true, productUoMDecimals] });
        };

        const formatCurrency = (value, hasSymbol = true) => {
            return formatMonetary(value, {
                currencyId: currency.id,
                noSymbol: !hasSymbol,
            });
        };

        const roundCurrency = (value) => {
            return roundDecimals(value, currency.decimal_places);
        };

        env.utils = {
            formatCurrency,
            roundCurrency,
            formatProductQty,
        };
    },
};

registry.category("services").add("contextual_utils_service", contextualUtilsService);
