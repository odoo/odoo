/** @odoo-module */

import { formatMonetary } from "@web/views/fields/formatters";
import { formatFloat, roundDecimals } from "@web/core/utils/numbers";
import { escapeRegExp } from "@web/core/utils/strings";
import { registry } from "@web/core/registry";

/**
 * This service introduces `utils` namespace in the `env` which can contain
 * functions that are parameterized by the data in `pos` service.
 */
export const contextualUtilsService = {
    dependencies: ["pos", "localization"],
    start(env, { pos, localization }) {
        const currency = pos.currency;
        const productUoMDecimals = pos.dp["Product Unit of Measure"];
        const decimalPoint = localization.decimalPoint;
        const thousandsSep = localization.thousandsSep;
        // Replace the thousands separator and decimal point with regex-escaped versions
        const escapedDecimalPoint = escapeRegExp(decimalPoint);
        let floatRegex;
        if (thousandsSep) {
            const escapedThousandsSep = escapeRegExp(thousandsSep);
            floatRegex = new RegExp(
                `^-?(?:\\d+(${escapedThousandsSep}\\d+)*)?(?:${escapedDecimalPoint}\\d*)?$`
            );
        } else {
            floatRegex = new RegExp(`^-?(?:\\d+)?(?:${escapedDecimalPoint}\\d*)?$`);
        }

        const formatProductQty = (qty) => {
            return formatFloat(qty, { digits: [true, productUoMDecimals] });
        };

        const formatCurrency = (value, hasSymbol = true) => {
            value = parseFloat(value);
            return formatMonetary(value, {
                currencyId: currency.id,
                noSymbol: !hasSymbol,
            });
        };

        const roundCurrency = (value) => {
            return roundDecimals(value, currency.decimal_places);
        };

        const isValidFloat = (inputValue) => {
            return ![decimalPoint, "-"].includes(inputValue) && floatRegex.test(inputValue);
        };

        env.utils = {
            formatCurrency,
            roundCurrency,
            formatProductQty,
            isValidFloat,
        };
    },
};

registry.category("services").add("contextual_utils_service", contextualUtilsService);
