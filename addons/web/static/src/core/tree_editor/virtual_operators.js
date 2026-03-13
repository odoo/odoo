import {
    applyTransformations,
    areEqualTrees,
    cloneTree,
    condition,
    connector,
    expression,
    FALSE_TREE,
    isTree,
    normalizeValue,
    operate,
    rewriteNConsecutiveChildren,
    TRUE_TREE,
} from "./condition_tree";
import { parseRelativeValue } from "./utils";

function splitPath(path, is_property) {
    if (typeof path !== "string" || path === "") {
        return { initialPath: "", lastPart: "" };
    }

    const pathParts = path.split(".");
    if (is_property && pathParts.length >= 2) {
        return {
            initialPath: pathParts.slice(0, -2).join("."),
            lastPart: pathParts.slice(-2).join("."),
        };
    }

    const lastPart = pathParts.pop() || "";
    const initialPath = pathParts.join(".");
    return { initialPath, lastPart };
}

function isSimplePath(path, isProperty) {
    return typeof path === "string" && !splitPath(path, isProperty).initialPath;
}

function wrapInAny(tree, initialPath, negate) {
    let con = cloneTree(tree);
    if (initialPath) {
        con = condition(initialPath, "any", con);
    }
    con.negate = negate;
    return con;
}

function introduceSetOperators(tree, options = {}) {
    function _introduceSetOperator(c, options = {}) {
        const { negate, path, operator, value } = c;
        const fieldType = options.getFieldDef?.(path)?.type;
        if (["=", "!="].includes(operator)) {
            if (fieldType) {
                if (fieldType === "boolean" && value === true) {
                    return condition(path, operator === "=" ? "set" : "not set", value, negate);
                } else if (
                    !["many2one", "date", "datetime"].includes(fieldType) &&
                    value === false
                ) {
                    return condition(path, operator === "=" ? "not set" : "set", value, negate);
                }
            }
        }
    }
    return operate(_introduceSetOperator, tree, options);
}

function eliminateSetOperators(tree) {
    function _removeSetOperator(c) {
        const { negate, path, operator, value, isProperty } = c;
        if (["set", "not set"].includes(operator)) {
            if (value === true) {
                return condition(path, operator === "set" ? "=" : "!=", value, negate, isProperty);
            }
            return condition(path, operator === "set" ? "!=" : "=", value, negate, isProperty);
        }
    }
    return operate(_removeSetOperator, tree);
}

function introduceStartsWithOperators(tree, options) {
    function _introduceStartsWithOperator(c, options) {
        const { negate, path, operator, value, isProperty } = c;
        const fieldType = options.getFieldDef?.(path)?.type;
        if (
            ["char", "text", "html"].includes(fieldType) &&
            operator === "=ilike" &&
            typeof value === "string"
        ) {
            if (value.endsWith("%")) {
                return condition(path, "starts with", value.slice(0, -1), negate, isProperty);
            }
        }
    }
    return operate(_introduceStartsWithOperator, tree, options);
}

function eliminateStartsWithOperators(tree) {
    function _eliminateStartsWithOperator(c) {
        const { negate, path, operator, value, isProperty } = c;
        if (operator === "starts with") {
            return condition(path, "=ilike", `${value}%`, negate, isProperty);
        }
    }
    return operate(_eliminateStartsWithOperator, tree);
}

function isSimpleAnd(c) {
    if (
        c.type === "connector" &&
        c.value === "&" &&
        !c.negate &&
        c.children.length === 2 &&
        c.children.every((child) => child.type === "condition" && !child.negate)
    ) {
        return true;
    }
    return false;
}

function isBetween(c) {
    const [{ path: p1, operator: op1, value: value1 }, { path: p2, operator: op2, value: value2 }] =
        c.children;
    if (p1 === p2 && op1 === ">=" && op2 === "<=") {
        return { path: p1, value1, value2 };
    }
    return false;
}

function makeBetween(path, value1, value2, isProperty) {
    return connector("&", [
        condition(path, ">=", value1, false, isProperty),
        condition(path, "<=", value2, false, isProperty),
    ]);
}

function isStrictBetween(c) {
    const [{ path: p1, operator: op1, value: value1 }, { path: p2, operator: op2, value: value2 }] =
        c.children;
    if (p1 === p2 && op1 === ">=" && op2 === "<") {
        return { path: p1, value1, value2 };
    }
    return false;
}

function makeStrictBetween(path, value1, value2, isProperty) {
    return connector("&", [
        condition(path, ">=", value1, false, isProperty),
        condition(path, "<", value2, false, isProperty),
    ]);
}

/**
 * Returns the relative range if a domain syntax matches the relative range syntax (checking if range is today +/- xxx d/w/m/y)
 * PAST relativity: PATH >= "today -X d/w/y/m" AND < "today" OR Future relativity: PATH > "today" AND <= "today +X d/w/y/m"
 * For DATETIMEs FUTURE relativity we expect 1 day offset to both side of the equation because today means today at 00:00
 * --> it takes the form of PATH > "today + 1d" AND <= "today +X w/m/y + 1d"
 * @param {Condition} c
 * @param {string} fieldType date and datetime supported for relativeBetween
 * @returns {boolean|Object} returns false if not a relative range compared to today
 */
function isRelativeBetween(c, fieldType) {
    const [c1, c2] = c.children;
    const p1 = parseRelativeValue(c1.value);
    const p2 = parseRelativeValue(c2.value);

    if (c1.path !== c2.path || !p1 || !p2) {
        return false;
    }

    const items = [
        { operator: c1.operator, diff: p1.diff, unit: p1.unit, offsetDays: p1.offsetDays },
        { operator: c2.operator, diff: p2.diff, unit: p2.unit, offsetDays: p2.offsetDays },
    ];

    // Sort by absolute difference. The one closest to 0 (today) becomes the first item.
    // We want the parser to detect regardless of the order (ie. today can be left or right)
    items.sort((a, b) => Math.abs(a.diff) - Math.abs(b.diff));
    const [today, other] = items;

    const pastRelativity = today.operator === "<" && other.operator === ">=" && other.diff < 0;
    const futureRelativity = today.operator === ">" && other.operator === "<=" && other.diff >= 0;

    if (pastRelativity || (futureRelativity && fieldType === "date")) {
        const isAnchorToday = today.unit === "day" && today.offsetDays === 0 && today.diff === 0;
        const isValidDayRange = isAnchorToday && other.offsetDays === 0;
        return isValidDayRange ? { diff: other.diff, unit: other.unit } : false;
    } else if (futureRelativity && fieldType === "datetime") {
        const isAnchorTomorrow = today.diff === 1 && today.unit === "day";
        if (other.unit === "day") {
            // e.g., > today + 1d AND <= today + 5d  => range of 4 days
            const isValidDayRange = isAnchorTomorrow && other.offsetDays === 0;
            return isValidDayRange ? { diff: other.diff - 1, unit: "day" } : false;
        } else {
            // e.g., > today + 1d AND <= today + 1w + 1d => range of 1 week
            const isValidDayRange = isAnchorTomorrow && other.offsetDays === 1;
            return isValidDayRange ? { diff: other.diff, unit: other.unit } : false;
        }
    }
    return false;
}

/**
 * Creates a domain range condition between today and a relative offset.
 * @param {string} path - Field name.
 * @param {number} diff - Magnitude of time shift.
 * @param {string} unit - 'day', 'week', 'month', or 'year'.
 * @param {boolean} isProperty - True if field is a metadata property.
 * @param {boolean} smartDates - Use shorthand keywords instead of expressions.
 * @param {'date'|'datetime'} fieldType - Field type for formatting/offset logic.
 * @returns {Condition} A combined domain condition (AND).
 */
function makeRelativeBetween(path, diff, unit, isProperty, smartDates, fieldType) {
    const isFuture = diff > 0;
    let todayCond, diffCond;

    if (smartDates) {
        const smartUnit = { week: "w", month: "m", year: "y" }[unit] || "d";
        todayCond = "today";
        diffCond = isFuture ? `today +${diff}${smartUnit}` : `today ${diff}${smartUnit}`;

        // Edge cases
        if (diff === 0) {
            todayCond = "today +1d"; // To match TODAY smart date format
            diffCond = "today";
        } else if (isFuture && fieldType === "datetime") {
            const futureOffset = smartUnit === "d" ? `${diff + 1}d` : `${diff}${smartUnit} +1d`;
            todayCond = "today +1d"; // because today == today 00:00 in datetimes
            diffCond = `today +${futureOffset}`;
        }
    } else {
        todayCond = getRelativeDateExpr(fieldType);
        diffCond = getRelativeDateExpr(fieldType, [`${unit}s = ${diff}`]);

        // Edge cases
        if (diff === 0) {
            todayCond = getRelativeDateExpr(fieldType, ["days=1"]);
            diffCond = getRelativeDateExpr(fieldType);
        } else if (isFuture && fieldType === "datetime") {
            const offset = unit === "day" ? [`days=${diff + 1}`] : [`${unit}s=${diff}`, "days=1"];
            todayCond = getRelativeDateExpr(fieldType, ["days=1"]);
            diffCond = getRelativeDateExpr(fieldType, offset);
        }
    }
    // return the lowest date first, makes more sense when reading domain in debug mode
    return connector("&", [
        condition(path, isFuture ? ">" : ">=", isFuture ? todayCond : diffCond, false, isProperty),
        condition(path, isFuture ? "<=" : "<", isFuture ? diffCond : todayCond, false, isProperty),
    ]);
}

/**
 * Helper to build the chained relativedelta string
 * e.g. ["months=1", "days=1"] -> "relativedelta(months=1) + relativedelta(days=1)"
 */
function buildDeltaExpr(deltas) {
    const arr = Array.isArray(deltas) ? deltas : deltas ? [deltas] : [];
    if (arr.length === 0) {
        return null;
    }
    return arr.map((d) => `relativedelta(${d})`).join(" + ");
}

export function boundDate(deltas) {
    const deltaExpr = buildDeltaExpr(deltas);
    if (!deltaExpr) {
        return expression(`context_today().strftime("%Y-%m-%d")`);
    }
    return expression(`(context_today() + ${deltaExpr}).strftime('%Y-%m-%d')`);
}

export function boundDatetime(deltas) {
    const deltaExpr = buildDeltaExpr(deltas);
    if (!deltaExpr) {
        return expression(
            `datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
        );
    }
    return expression(
        `datetime.datetime.combine(context_today() + ${deltaExpr}, datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
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
const BOUNDS_DATE = DELTAS.map(([k, l, r]) => [k, boundDate(l), boundDate(r)]);
const BOUNDS_DATETIME = DELTAS.map(([k, l, r]) => [k, boundDatetime(l), boundDatetime(r)]);

function getBounds(generateSmartDates, fieldType) {
    return generateSmartDates
        ? BOUNDS_SMART_DATES
        : fieldType === "date"
        ? BOUNDS_DATE
        : BOUNDS_DATETIME;
}

function introduceInRangeOperators(tree, options = {}) {
    function _introduceInRangeOperator(c, options) {
        const path = c.children[0].path;
        const fieldType = options.getFieldDef?.(path)?.type;
        const isProperty = c.children[0].isProperty;
        const isDate = ["date", "datetime"].includes(fieldType);
        if (!isSimpleAnd(c) || !isDate || !isSimplePath(c.children[0].path, isProperty)) {
            return;
        }
        const generateSmartDates = options.generateSmartDates ?? true;
        let res = isStrictBetween(c);
        if (res) {
            const bounds = getBounds(generateSmartDates, fieldType);
            for (const [valueType, leftBound, rightBound] of bounds) {
                if (
                    generateSmartDates
                        ? res.value1 === leftBound && res.value2 === rightBound
                        : res.value1._expr === leftBound._expr &&
                          res.value2._expr === rightBound._expr
                ) {
                    return condition(
                        path,
                        "in range",
                        [fieldType, valueType, false, false],
                        false,
                        isProperty
                    );
                }
            }
        }
        res = isRelativeBetween(c, fieldType);
        if (res) {
            const value = [fieldType, "relativeRange", res.diff, res.unit];
            return condition(path, "in range", value);
        }
        res = isBetween(c);
        if (res) {
            const { path, value1, value2 } = res;
            return condition(
                path,
                "in range",
                [
                    fieldType,
                    "dateRange",
                    // @ts-ignore
                    ...normalizeValue([value1, value2]),
                ],
                false,
                isProperty
            );
        }
    }
    return operate(
        rewriteNConsecutiveChildren(_introduceInRangeOperator),
        tree,
        options,
        "connector"
    );
}

function eliminateInRangeOperators(tree, options = {}) {
    function _eliminateInRangeOperator(c, options) {
        const { negate, path, operator, value, isProperty } = c;
        // @ts-ignore
        if (operator !== "in range") {
            return;
        }
        const { initialPath, lastPart } = splitPath(path, isProperty);
        const [fieldType, valueType, value1, value2] = value;
        const smartDates = options.generateSmartDates ?? true;
        let tree;
        if (valueType === "dateRange") {
            tree = makeBetween(lastPart, value1, value2, isProperty);
        } else if (valueType === "relativeRange") {
            tree = makeRelativeBetween(lastPart, value1, value2, isProperty, smartDates, fieldType);
        } else {
            const bounds = getBounds(smartDates, fieldType);
            const [, leftBound, rightBound] = bounds.find(([v]) => v === valueType);
            tree = makeStrictBetween(lastPart, leftBound, rightBound, isProperty);
        }
        return wrapInAny(tree, initialPath, negate);
    }
    return operate(_eliminateInRangeOperator, tree, options);
}

function introduceBetweenOperators(tree, options = {}) {
    function _introduceBetweenOperator(c, options) {
        const res = isBetween(c);
        if (!res) {
            return;
        }
        // @ts-ignore
        const { path, value1, value2 } = res;
        const fieldType = options.getFieldDef?.(path)?.type;
        if (["integer", "float", "monetary"].includes(fieldType) && isSimplePath(path)) {
            return condition(path, "between", normalizeValue([value1, value2]));
        }
    }
    return operate(
        rewriteNConsecutiveChildren(_introduceBetweenOperator),
        tree,
        options,
        "connector"
    );
}

function eliminateBetweenOperators(tree) {
    function _eliminateBetweenOperator(c) {
        const { negate, path, operator, value, isProperty } = c;
        // @ts-ignore
        if (operator !== "between") {
            return;
        }
        const { initialPath, lastPart } = splitPath(path, isProperty);
        return wrapInAny(
            makeBetween(lastPart, value[0], value[1], isProperty),
            initialPath,
            negate
        );
    }
    return operate(_eliminateBetweenOperator, tree);
}

function _eliminateAnyOperator(c) {
    const { path, operator, value, negate } = c;
    if (
        operator === "any" &&
        isTree(value) &&
        value.type === "condition" &&
        typeof path === "string" &&
        typeof value.path === "string" &&
        !negate &&
        !value.negate &&
        ["between", "in range"].includes(value.operator)
    ) {
        return condition(
            `${path}.${value.path}`,
            value.operator,
            value.value,
            false,
            value.isProperty
        );
    }
}

function eliminateAnyOperators(tree) {
    return operate(_eliminateAnyOperator, tree);
}

function removeFalseTrueLeaves(tree) {
    function _removeFalseTrueLeave(c) {
        const { path, operator, value, negate, isProperty } = c;
        if (areEqualTrees(condition(path, operator, value, false, isProperty), FALSE_TREE)) {
            return connector(negate ? "&" : "|", []);
        }
        if (areEqualTrees(condition(path, operator, value, false, isProperty), TRUE_TREE)) {
            return connector(negate ? "|" : "&", []);
        }
    }
    return operate(_removeFalseTrueLeave, tree);
}

export function introduceVirtualOperators(tree, options = {}) {
    return applyTransformations(
        [
            eliminateAnyOperators,
            introduceSetOperators,
            introduceStartsWithOperators,
            introduceBetweenOperators,
            introduceInRangeOperators,
        ],
        tree,
        options
    );
}

export function eliminateVirtualOperators(tree, options = {}) {
    return applyTransformations(
        [
            eliminateInRangeOperators,
            eliminateBetweenOperators,
            eliminateStartsWithOperators,
            eliminateSetOperators,
        ],
        tree,
        options
    );
}

export function areEquivalentTrees(tree, otherTree) {
    const simplifiedTree = removeFalseTrueLeaves(eliminateVirtualOperators(tree));
    const otherSimplifiedTree = removeFalseTrueLeaves(eliminateVirtualOperators(otherTree));
    return areEqualTrees(simplifiedTree, otherSimplifiedTree);
}
