import { registry } from "@web/core/registry";
import { formatFloatTime } from "@web/views/fields/formatters";

export function formatFloatTimeDays(value, options = {}) {
    let result = formatFloatTime(value, options);

    const duration = result.split(" ");
    const hours = parseInt(duration[0].slice(0, -1));
    if (duration[0].slice(-1) == 'h' && hours >= 24) {
        const days = Math.floor(hours / 24);
        const daysString = `${days}d ${hours % 24}h`;
        result = [daysString, ...duration.slice(1)].join(" ")
    }

    return result;
}
formatFloatTimeDays.extractOptions = formatFloatTime.extractOptions;

registry.category("formatters").add("float_time_days", formatFloatTimeDays);
