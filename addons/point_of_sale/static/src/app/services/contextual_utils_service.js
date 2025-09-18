import { registry } from "@web/core/registry";
import { formatFloat } from "@web/core/utils/format/numbers";
import { escapeRegExp } from "@web/core/utils/format/strings";
import { parseFloat } from "@web/fields/parsers";
import { formatCurrency as webFormatCurrency } from "@web/services/currency";
/**
 * This service introduces `utils` namespace in the `env` which can contain
 * functions that are parameterized by the data in `pos` service.
 */
export const contextualUtilsService = {
    dependencies: ["pos", "localization"],
    start(env, { pos, localization }) {
        const res_currency = pos.currency;
        const ProductUnit = pos.data.models["decimal.precision"].find(
            (dp) => dp.name === "Product Unit",
        );
        const decimalPoint = localization.decimalPoint;
        const thousandsSep = localization.thousandsSep;
        // Replace the thousands separator and decimal point with regex-escaped versions
        const escapedDecimalPoint = escapeRegExp(decimalPoint);
        let floatRegex;
        if (thousandsSep) {
            const escapedThousandsSep = escapeRegExp(thousandsSep);
            floatRegex = new RegExp(
                `^-?(?:\\d+(${escapedThousandsSep}\\d+)*)?(?:${escapedDecimalPoint}\\d*)?$`,
            );
        } else {
            floatRegex = new RegExp(`^-?(?:\\d+)?(?:${escapedDecimalPoint}\\d*)?$`);
        }

        const formatProductQty = (qty, trailingZeros = true) =>
            formatFloat(qty, {
                digits: [true, ProductUnit.digits],
                trailingZeros: trailingZeros,
            });

        const formatCurrency = (value, hasSymbol = true) =>
            webFormatCurrency(value, res_currency.id, {
                noSymbol: !hasSymbol,
            });

        const roundCurrency = (value) => res_currency.round(value);

        const isValidFloat = (inputValue) =>
            ![decimalPoint, "-"].includes(inputValue) && floatRegex.test(inputValue);

        const parseValidFloat = (inputValue) =>
            isValidFloat(inputValue) ? parseFloat(inputValue) : 0;

        env.utils = {
            formatCurrency,
            roundCurrency,
            formatProductQty,
            isValidFloat,
            parseValidFloat,
        };
    },
};
registry.category("services").add("contextual_utils_service", contextualUtilsService);
