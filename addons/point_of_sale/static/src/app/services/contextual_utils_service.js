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
            (dp) => dp.name === "Product Unit"
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

<<<<<<< saas-18.1:addons/point_of_sale/static/src/app/services/contextual_utils_service.js
        const formatProductQty = (qty) => formatFloat(qty, { digits: [true, productUoMDecimals] });
||||||| 4209d441afa058a87e142b44d6e33a546741dd2b:addons/point_of_sale/static/src/app/utils/contextual_utils_service.js
        const formatProductQty = (qty) => {
            return formatFloat(qty, { digits: [true, productUoMDecimals] });
        };
=======
        const formatProductQty = (qty, trailingZeros = true) => {
            return formatFloat(qty, {
                digits: [true, productUoMDecimals],
                trailingZeros: trailingZeros,
            });
        };
>>>>>>> f8acdaf3e3b338d8cd0d76ba94e8d6b810a28091:addons/point_of_sale/static/src/app/utils/contextual_utils_service.js

        const formatCurrency = (value, hasSymbol = true) =>
            webFormatCurrency(value, res_currency.id, {
                noSymbol: !hasSymbol,
            });
        const floatIsZero = (value) => genericFloatIsZero(value, res_currency.decimal_places);

        const roundCurrency = (value) => roundDecimals(value, res_currency.decimal_places);

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
            floatIsZero,
        };
    },
};
registry.category("services").add("contextual_utils_service", contextualUtilsService);
