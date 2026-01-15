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

export function getFormattedDateSpan(start, end) {
    const isSameDay = start.hasSame(end, "days");

    if (!isSameDay && start.hasSame(end, "month")) {
        // Simplify date-range if an event occurs into the same month (eg. "August 4-5, 2019")
        return start.toFormat("LLLL d") + "-" + end.toFormat("d, y");
    } else {
        return isSameDay
            ? start.toFormat("DDD")
            : start.toFormat("DDD") + " - " + end.toFormat("DDD");
    }
}
