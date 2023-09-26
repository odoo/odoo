/** @odoo-module */

import { formatMonetary } from "@web/views/fields/formatters";
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
    dependencies: ["pos_data", "localization"],
    start(env, { pos_data, localization }) {
        const cache = {
            company: pos_data["res.company"],
            currency: pos_data["res.currency"],
            pricelists: pos_data["product.pricelist"],
            uom_unit_id: pos_data["uom_unit_id"],
            config: pos_data["pos.config"],
            base_url: pos_data["base_url"],
            dp: pos_data["decimal.precision"],
            picking_type: pos_data["stock.picking.type"],

            taxes_by_id: pos_data["taxes_by_id"],
            units_by_id: pos_data["units_by_id"],
        };

        const productUoMDecimals = cache.dp["Product Unit of Measure"];
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

        const formatStrCurrency = (valueStr, hasSymbol = true) => {
            return formatCurrency(parseFloat(valueStr), hasSymbol);
        };

        const formatCurrency = (value, hasSymbol = true) => {
            return formatMonetary(value, {
                currencyId: cache.currency.id,
                noSymbol: !hasSymbol,
            });
        };
        const floatIsZero = (value) => {
            return genericFloatIsZero(value, cache.currency.decimal_places);
        };

        const roundCurrency = (value) => {
            return roundDecimals(value, cache.currency.decimal_places);
        };

        const isValidFloat = (inputValue) => {
            return ![decimalPoint, "-"].includes(inputValue) && floatRegex.test(inputValue);
        };

        env.utils = {
            formatCurrency,
            formatStrCurrency,
            roundCurrency,
            formatProductQty,
            isValidFloat,
            floatIsZero,
        };
        env.cache = cache;
    },
};

registry.category("services").add("contextual_utils_service", contextualUtilsService);
