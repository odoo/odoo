/** @odoo-module */

import { formatMonetary } from "@web/views/fields/formatters";
import { registry } from "@web/core/registry";

/**
 * This service introduces `utils` namespace in the `env` which can contain
 * functions that are parameterized by the data in `pos` service.
 */
export const contextualUtilsService = {
    dependencies: ["pos"],
    start(env, { pos }) {
        const currency = pos.globalState.currency;

        const formatCurrency = (value, hasSymbol = true) => {
            return formatMonetary(value, {
                currencyId: currency.id,
                noSymbol: !hasSymbol,
            });
        };

        env.utils = {
            formatCurrency,
        };
    },
};

registry.category("services").add("contextual_utils_service", contextualUtilsService);
