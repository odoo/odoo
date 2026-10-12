import { registry } from "@web/core/registry";
import { formatFloat } from "@web/core/utils/numbers";

export function formatFullRangePercentage(value, options = {}) {
    value = value || 0;
    options = Object.assign({ trailingZeros: false, thousandsSep: "" }, options);
    if (!options.digits && options.field) {
        options.digits = options.field.digits;
    }
    const formatted = formatFloat(value, options);
    return `${formatted}${options.noSymbol ? "" : "%"}`;
}

/**
 * Add the format function to the global `formatters` as it will be used by the
 * `ListRenderer.computeAggregates` when trying to format the value provided by
 * the `full_range_percentage` widget.
 */
registry.category("formatters").add("full_range_percentage", formatFullRangePercentage);
