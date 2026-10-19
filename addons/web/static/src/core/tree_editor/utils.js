import { expression } from "./condition_tree";

export function disambiguate(value, displayNames) {
    if (!Array.isArray(value)) {
        return value === "";
    }
    let hasSomeString = false;
    let hasSomethingElse = false;
    for (const val of value) {
        if (val === "") {
            return true;
        }
        if (typeof val === "string" || (displayNames && isId(val))) {
            hasSomeString = true;
        } else {
            hasSomethingElse = true;
        }
    }
    return hasSomeString && hasSomethingElse;
}

export function isId(value) {
    return Number.isInteger(value) && value >= 1;
}

export function getResModel(fieldDef) {
    if (fieldDef) {
        return fieldDef.is_property ? fieldDef.comodel : fieldDef.relation;
    }
    return null;
}

const SPECIAL_FIELDS = ["country_id", "user_id", "partner_id", "stage_id", "id"];

export function getDefaultPath(fieldDefs) {
    for (const name of SPECIAL_FIELDS) {
        const fieldDef = fieldDefs[name];
        if (fieldDef) {
            return fieldDef.name;
        }
    }
    const name = Object.keys(fieldDefs)[0];
    if (name) {
        return name;
    }
    throw new Error(`No field found`);
}

// --- Date range utils, used by ExpressionEditor --- //

/**
 * Generates an relativedelta expression string for a date or datetime relative to today.
 * @param {'date' | 'datetime'} type - The field type determining the string format
 * @param {string | array} [delta] - Relativedelta arguments (e.g., "days=-2", [weeks=2, "days=1"] ).
 * @returns {Expression} An expression object containing the formatted Python string. Returns today if delta is null
 */
export function getRelativeDateExpr(type, delta) {
    const isDate = type === "date";
    const deltaStr = delta ? ` + relativedelta(${delta})` : "";

    if (isDate) {
        return expression(`(context_today()${deltaStr}).strftime("%Y-%m-%d")`);
    }

    return expression(
        `datetime.datetime.combine(context_today()${deltaStr}, datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
    );
}

const BOUNDS_SMART_DATES = [
    ["today", "today", "today +1d"],
    ["last7Days", "today -7d", "today"],
    ["last30Days", "today -30d", "today"],
    ["monthToDate", "today =1d", "today +1d"],
    ["lastMonth", "today =1d -1m", "today =1d"],
    ["yearToDate", "today =1m =1d", "today +1d"],
    ["last365Days", "today -365d", "today"],
];
const DELTAS = [
    ["today", "", "days = 1"],
    ["last7Days", "days = -7", ""],
    ["last30Days", "days = -30", ""],
    ["monthToDate", "day = 1", "days = 1"],
    ["lastMonth", "day = 1, months = -1", "day = 1"],
    ["yearToDate", "day = 1, month = 1", "days = 1"],
    ["last365Days", "days = -365", ""],
];
const BOUNDS_DATE = DELTAS.map(([k, l, r]) => [
    k,
    getRelativeDateExpr("date", l),
    getRelativeDateExpr("date", r),
]);
const BOUNDS_DATETIME = DELTAS.map(([k, l, r]) => [
    k,
    getRelativeDateExpr("datetime", l),
    getRelativeDateExpr("datetime", r),
]);

/**
 * Retrieves the appropriate date range syntax for hardcoded options (last 7 days ..)
 * @param {boolean} generateSmartDates - Whether to return human-readable odoo syntax (today + 1d)
 * @param {'date'|'datetime'} fieldType - The data type of the field, used to select the syntax
 * @returns {Object[]} An array of bound definition (eg. ["last30Days", "today -30d", "today"])
 */
export function getBounds(generateSmartDates, fieldType) {
    if (generateSmartDates) {
        return BOUNDS_SMART_DATES;
    }
    return fieldType === "date" ? BOUNDS_DATE : BOUNDS_DATETIME;
}

/**
 * Parses a relative date string or domain expression into a standardized diff, unit, and offset.
 * - "today - 5d"         --> { diff: -5, unit: "day", offsetDays: 0 }
 * - "today + 2w + 1d"    --> { diff: 2,  unit: "week", offsetDays: 1 }
 * - "relativedelta(m=-2)"--> { diff: -2, unit: "month", offsetDays: 0 }
 * - "today"              --> { diff: 0,  unit: "day", offsetDays: 0 }
 * @param {string | { _expr: string }} val - The relative date string
 * @returns {{ diff: number, unit: "day" | "week" | "month" | "year", offsetDays: number } | null}
 */
export function parseRelativeValue(val) {
    if (typeof val === "string") {
        const trimmed = val.trim();
        if (trimmed === "today") {
            return { diff: 0, unit: "day", offsetDays: 0 };
        }
        // Regex captures: 1: sign, 2: value, 3: unit, 4: optional day offset (e.g., " + 1d")
        const match = trimmed.match(/^today\s*([+-])\s*(\d+)\s*([dwmy])(?:\s*\+\s*(\d+)d)?$/);
        if (match) {
            const unitMap = { d: "day", w: "week", m: "month", y: "year" };
            return {
                diff: Number(match[1] + match[2]),
                unit: unitMap[match[3]],
                offsetDays: match[4] ? Number(match[4]) : 0,
            };
        }
    } else if (val?._expr && typeof val._expr === "string") {
        const expr = val._expr;
        const matches = [...expr.matchAll(/(days|weeks|months|years)\s*=\s*([+-]?\d+)/g)];

        if (matches.length === 0) {
            const isToday = expr.includes("context_today()");
            return isToday ? { diff: 0, unit: "day", offsetDays: 0 } : null;
        }

        let mainMatch = matches[0];
        let offsetDays = 0;

        if (matches.length > 1) {
            const offsetIndex = matches.findIndex((m) => m[1] === "days" && Number(m[2]) > 0);
            if (offsetIndex !== -1) {
                offsetDays = Number(matches[offsetIndex][2]);
                mainMatch = matches[offsetIndex === 0 ? 1 : 0];
            }
        }

        return {
            diff: Number(mainMatch[2]),
            unit: mainMatch[1].slice(0, -1), // "months" -> "month"
            offsetDays: offsetDays,
        };
    }
    return null;
}
