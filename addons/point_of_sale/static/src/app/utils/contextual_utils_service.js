import { formatCurrency as webFormatCurrency } from "@web/core/currency";
import {
    formatFloat,
    roundDecimals,
    floatIsZero as genericFloatIsZero,
} from "@web/core/utils/numbers";
import { escapeRegExp } from "@web/core/utils/strings";
import { registry } from "@web/core/registry";
import { parseFloat } from "@web/views/fields/parsers";

/**
 * This service introduces `utils` namespace in the `env` which can contain
 * functions that are parameterized by the data in `pos` service.
 */
export const contextualUtilsService = {
    dependencies: ["pos", "localization"],
    start(env, { pos, localization }) {
        const res_currency = pos.currency;
        const productUoMDecimals = pos.data.models["decimal.precision"].find(
            (dp) => dp.name === "Product Unit of Measure"
        ).digits;
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

        const formatProductQty = (qty, trailingZeros = true) => {
            return formatFloat(qty, {
                digits: [true, productUoMDecimals],
                trailingZeros: trailingZeros,
            });
        };

        const formatCurrency = (value, hasSymbol = true) => {
            return webFormatCurrency(value, res_currency.id, {
                noSymbol: !hasSymbol,
            });
        };
        const floatIsZero = (value) => {
            return genericFloatIsZero(value, res_currency.decimal_places);
        };

        const roundCurrency = (value) => {
            return roundDecimals(value, res_currency.decimal_places);
        };

        const isValidFloat = (inputValue) => {
            return ![decimalPoint, "-"].includes(inputValue) && floatRegex.test(inputValue);
        };

        const parseValidFloat = (inputValue) => {
            return isValidFloat(inputValue) ? parseFloat(inputValue) : 0;
        };

        env.utils = {
            formatCurrency,
            roundCurrency,
            formatProductQty,
            isValidFloat,
            parseValidFloat,
            floatIsZero,
        };
    },
};
registry.category("services").add("contextual_utils_service", contextualUtilsService);
