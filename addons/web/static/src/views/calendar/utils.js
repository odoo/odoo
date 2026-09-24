export function convertRecordToEvent(record, forceAllDay = false) {
    const allDay =
        forceAllDay || record.isAllDay || record.end.diff(record.start, "hours").hours >= 24;
    let end = record.end;
    if (record.isAllDay || (allDay && end.toMillis() !== end.startOf("day").toMillis())) {
        end = end.plus({ days: 1 });
    }
    return {
        id: record.id,
        title: record.title,
        start: record.start.toISO(),
        end: end.toISO(),
        allDay,
    };
}

const CSS_COLOR_REGEX =
    /^((#[A-F0-9]{3})|(#[A-F0-9]{6})|((hsl|rgb)a?\(\s*(?:(\s*\d{1,3}%?\s*),?){3}(\s*,[0-9.]{1,4})?\))|)$/i;
const colorMap = new Map();
export function getColor(key) {
    if (!key) {
        return false;
    }
    if (colorMap.has(key)) {
        return colorMap.get(key);
    }

    // check if the key is a css color
    if (typeof key === "string" && key.match(CSS_COLOR_REGEX)) {
        colorMap.set(key, key);
    } else if (typeof key === "number") {
        colorMap.set(key, ((key - 1) % 55) + 1);
    } else {
        colorMap.set(key, (((colorMap.size + 1) * 5) % 24) + 1);
    }

    return colorMap.get(key);
}

/**
 * Formats a date span between two dates with various formatting options.
 * @param {DateTime} start
 * @param {DateTime} end
 * @param {Object} options
 * @param {string} [options.sameDayFormat] - Format string for when start and end are the same day. If not provided, the default is "DDD".
 * @returns {string}
 */
export function getFormattedDateSpan(start, end, options = {}) {
    const isSameDay = start.hasSame(end, "days");

    if (!isSameDay && start.hasSame(end, "month")) {
        // Simplify date-range if an event occurs into the same month (eg. "August 4-5, 2019")
        return start.toFormat("LLLL d") + "-" + end.toFormat("d, y");
    } else {
        return isSameDay
            ? start.toFormat(options.sameDayFormat ?? "DDD")
            : start.toFormat("DDD") + " - " + end.toFormat("DDD");
    }
}

export function joinClasses(...classes) {
    return classes.flat().filter(Boolean).join(" ");
}

/**
 * Luxon format strings (e.g. `dayHeaderFormat: "EEE d"`) were handled by the luxon3 plugin,
 * removed in v7.
 */
const luxonFormatPlugin = {
    name: "odoo-luxon-format",
    cmdFormatter: (format, { date, timeZone, localeCodes }) => {
        const [year, month, day, hour, minute, second, millisecond] = date.array;
        return luxon.DateTime.fromObject(
            { year, month: month + 1, day, hour, minute, second, millisecond },
            { zone: timeZone, locale: localeCodes[0] }
        ).toFormat(format);
    },
};

/**
 * Time zones are resolved by Temporal, which only accepts IANA names and offsets, whereas the
 * luxon3 plugin also accepted luxon fixed-offset zone names (e.g. "UTC+1").
 */
function toTemporalTimeZone(name) {
    const zone = luxon.Info.normalizeZone(name);
    return zone.isUniversal ? zone.formatOffset(0, "short") : zone.name;
}

const CLASS_OPTION_RE = /(^c|C)lass(Name)?$/;

/**
 * The class options accepted arrays in v6, v7 only accepts strings (an array is dropped when the
 * option is joined with the one of a plugin, e.g. the theme).
 */
function toClassString(classes) {
    return typeof classes === "function"
        ? (info) => joinClasses(classes(info))
        : joinClasses(classes);
}

/**
 * @param {Object} options FullCalendar options
 * @returns {Object} options completed with what Odoo relies on from FullCalendar v6
 */
export function withCompatOptions(options) {
    const result = {
        ...options,
        plugins: [luxonFormatPlugin, ...(options.plugins || [])],
        timeZone: toTemporalTimeZone(options.timeZone),
    };
    for (const name in options) {
        if (CLASS_OPTION_RE.test(name)) {
            result[name] = toClassString(options[name]);
        }
    }
    return result;
}
