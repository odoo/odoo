import { registry } from "@web/core/registry";
import { formatFloat } from "@web/core/utils/numbers";

export function formatMailingPercentage(value, options = {}) {
    value = value || 0;
    options = Object.assign({ trailingZeros: false, thousandsSep: "" }, options);
    if (!options.digits && options.field) {
        options.digits = options.field.digits;
    }
    const formatted = formatFloat(value, options);
    return `${formatted}${options.noSymbol ? "" : "%"}`;
}

/**
 * Used by the `ListRenderer.computAggregates()`.
 */
registry.category("formatters").add("mailing-percentage", formatMailingPercentage);
