import {
    applyTransformations,
    areEqualTrees,
    cloneTree,
    condition,
    updateCondition,
    connector,
    isTree,
    normalizeValue,
    operate,
    FALSE_TREE,
    TRUE_TREE,
    rewriteNConsecutiveChildren,
} from "./condition_tree";
import { getRelativeDateExpr, getBounds, parseRelativeValue } from "./utils";

/** @typedef {import("./condition_tree").AST} AST */
/** @typedef {import("./condition_tree").Value} Value */
/** @typedef {import("./condition_tree").Condition} Condition */
/** @typedef {import("./condition_tree").Connector} Connector */
/** @typedef {import("./condition_tree").Tree} Tree */
/** @typedef {import("./condition_tree").Options} Options */

/**
 * Splits a condition's path into an initial segment and a final segment, handling property paths appropriately.
 * @param {Condition} c
 * @returns {{ initialPath: string, lastPart: string }}
 */
function splitPath(c) {
    if (typeof c.path !== "string" || c.path === "") {
        return { initialPath: "", lastPart: "" };
    }

    const pathParts = c.path.split(".");
    if (c.isProperty && pathParts.length >= 2) {
        return {
            initialPath: pathParts.slice(0, -2).join("."),
            lastPart: pathParts.slice(-2).join("."),
        };
    }

    const lastPart = pathParts.pop() || "";
    const initialPath = pathParts.join(".");
    return { initialPath, lastPart };
}

/**
 * Checks if a condition's path is a field string without dot notation (eg. properties).
 * @param {Condition} c
 * @returns {boolean}
 */
function isSimplePath(c) {
    return typeof c.path === "string" && !splitPath(c).initialPath;
}

/**
 * Wraps a given condition tree in an "any" operator condition using the specified initial path.
 * @param {Tree} tree
 * @param {string} initialPath
 * @param {boolean} [negate]
 * @returns {Tree}
 */
function wrapInAny(tree, initialPath, negate) {
    if (initialPath) {
        return condition(initialPath, "any", cloneTree(tree), negate);
    }
    return { ...cloneTree(tree), negate };
}

/**
 * Transforms `=` and `!=` operators into `set` and `not set` operators
 * @param {Tree} tree
 * @param {TreeOperatorOptions} options
 * @returns {Tree}
 */
function introduceSetOperators(tree, options = {}) {
    function _introduceSetOperator(c, options = {}) {
        const fieldType = options.getFieldDef?.(c.path)?.type;
        if (!["=", "!="].includes(c.operator) || !fieldType) {
            return;
        }
        if (fieldType === "boolean" && c.value === true) {
            return updateCondition(c, { operator: c.operator === "=" ? "set" : "not set" });
        } else if (!["many2one", "date", "datetime"].includes(fieldType) && c.value === false) {
            return updateCondition(c, { operator: c.operator === "=" ? "not set" : "set" });
        }
    }
    return operate(_introduceSetOperator, tree, options);
}

/**
 * Transforms `set` and `not set` operators into `=` and `!=` operators
 * @param {Tree} tree
 * @returns {Tree}
 */
function eliminateSetOperators(tree) {
    function _removeSetOperator(c) {
        if (["set", "not set"].includes(c.operator)) {
            const op = c.operator === "set" ? (c.value ? "=" : "!=") : c.value ? "!=" : "=";
            return updateCondition(c, { operator: op });
        }
    }
    return operate(_removeSetOperator, tree);
}

/**
 * Transforms `ilike` operators into `start with` operators
 * @param {Tree} tree
 * @param {TreeOperatorOptions} options
 * @returns {Tree}
 */
function introduceStartsWithOperators(tree, options) {
    function _introduceStartsWithOperator(c, options) {
        const fieldType = options.getFieldDef?.(c.path)?.type;
        if (
            ["char", "text", "html"].includes(fieldType) &&
            c.operator === "=ilike" &&
            typeof c.value === "string"
        ) {
            if (c.value.endsWith("%")) {
                return updateCondition(c, { operator: "starts with", value: c.value.slice(0, -1) });
            }
        }
    }
    return operate(_introduceStartsWithOperator, tree, options);
}

/**
 * Transforms `start with` operators into `ilike` operators
 * @param {Tree} tree
 * @returns {Tree}
 */
function eliminateStartsWithOperators(tree) {
    function _eliminateStartsWithOperator(c) {
        if (c.operator === "starts with") {
            return updateCondition(c, { operator: "=ilike", value: `${c.value}%` });
        }
    }
    return operate(_eliminateStartsWithOperator, tree);
}

/**
 * Checks if a condition is a simple (ie. no nesting) domain AND condition.
 * @param {Condition} c
 * @returns {boolean}
 */
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

/**
 * Checks if a condition matches the expected syntax of a between
 * @param {Condition} c The condition to assess
 * @returns {boolean}
 */
function isBetween(c) {
    const [{ path: p1, operator: op1, value: value1 }, { path: p2, operator: op2, value: value2 }] =
        c.children;
    if (p1 === p2 && op1 === ">=" && op2 === "<=") {
        return { path: p1, value1, value2 };
    }
    return false;
}

/**
 * Creates a domain range condition between 2 dates with a syntax that is interpreted as a between.
 * @param {string} path - Field name.
 * @param {'date'|'datetime'} value1 - first date
 * @param {'date'|'datetime'} value2 - second date
 * @param {boolean} isProperty - True if field is a metadata property.
 * @returns {Condition} A combined domain condition (AND).
 */
function makeBetween(path, value1, value2, isProperty) {
    return connector("&", [
        condition(path, ">=", value1, false, isProperty),
        condition(path, "<=", value2, false, isProperty),
    ]);
}

/**
 * Checks if a condition matches the expected syntax of a strict between
 * @param {Condition} c The condition to assess
 * @returns {boolean}
 */
function isStrictBetween(c) {
    const [{ path: p1, operator: op1, value: value1 }, { path: p2, operator: op2, value: value2 }] =
        c.children;
    if (p1 === p2 && op1 === ">=" && op2 === "<") {
        return { path: p1, value1, value2 };
    }
    return false;
}

/**
 * Creates a domain range condition between 2 dates with a syntax that is interpreted as a strict between.
 * @param {string} path - Field name.
 * @param {'date'|'datetime'} value1 - first date
 * @param {'date'|'datetime'} value2 - second date
 * @param {boolean} isProperty - True if field is a metadata property.
 * @returns {Condition} A combined domain condition (AND).
 */
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
 * Check if a tree can be interpreted as an in range operator (as a `strictBetween`, `relativeBetween` or `between`)
 * @param {Tree} tree
 * @param {TreeOperatorOptions} options
 * @returns {boolean}
 */
function introduceInRangeOperators(tree, options = {}) {
    function _introduceInRangeOperator(c, options) {
        const path = c.children[0].path;
        const fieldType = options.getFieldDef?.(path)?.type;
        const isProperty = c.children[0].isProperty;
        const isDate = ["date", "datetime"].includes(fieldType);
        if (!isSimpleAnd(c) || !isDate || !isSimplePath(c.children[0])) {
            return;
        }
        const generateSmartDates = options.generateSmartDates ?? true;
        const base = condition(path, "in range", "_replaced_below", false, isProperty);

        let res = isStrictBetween(c);
        if (res) {
            const bounds = getBounds(generateSmartDates, fieldType);
            const match = bounds.find(([, left, right]) =>
                generateSmartDates
                    ? res.value1 === left && res.value2 === right
                    : res.value1._expr === left._expr && res.value2._expr === right._expr
            );
            if (match) {
                return updateCondition(base, { value: [fieldType, match[0], false, false] });
            }
        }
        res = isRelativeBetween(c, fieldType);
        if (res) {
            return updateCondition(base, {
                value: [fieldType, "relativeRange", res.diff, res.unit],
            });
        }
        res = isBetween(c);
        if (res) {
            return updateCondition(base, {
                value: [fieldType, "dateRange", ...normalizeValue([res.value1, res.value2])],
            });
        }
    }
    return operate(
        rewriteNConsecutiveChildren(_introduceInRangeOperator),
        tree,
        options,
        "connector"
    );
}

/**
 * Expands "in range" operators into standard domain bounds, scoping nested paths with
 * an "any" condition to ensure both bounds apply to the exact same related record.
 * @param {Tree} tree
 * @param {TreeOperatorOptions} options
 * @returns {boolean}
 */
function eliminateInRangeOperators(tree, options = {}) {
    function _eliminateInRangeOperator(c, options) {
        if (c.operator !== "in range") {
            return;
        }
        const { initialPath, lastPart } = splitPath(c);
        const [fieldType, valueType, v1, v2] = c.value;
        const smartDates = options.generateSmartDates ?? true;
        let tree;
        if (valueType === "dateRange") {
            tree = makeBetween(lastPart, v1, v2, c.isProperty);
        } else if (valueType === "relativeRange") {
            tree = makeRelativeBetween(lastPart, v1, v2, c.isProperty, smartDates, fieldType);
        } else {
            const bounds = getBounds(smartDates, fieldType);
            const [, leftBound, rightBound] = bounds.find(([v]) => v === valueType);
            tree = makeStrictBetween(lastPart, leftBound, rightBound, c.isProperty);
        }
        return wrapInAny(tree, initialPath, c.negate);
    }
    return operate(_eliminateInRangeOperator, tree, options);
}

/**
 * Transforms standard numeric ranges into "between" virtual operators.
 * @param {Tree} tree
 * @param {TreeOperatorOptions} options
 * @returns {boolean}
 */
function introduceBetweenOperators(tree, options = {}) {
    function _introduceBetweenOperator(c, options) {
        const res = isBetween(c);
        if (!res) {
            return;
        }
        const { path, value1, value2 } = res;
        const fieldType = options.getFieldDef?.(path)?.type;
        const isProperty = c.children[0].isProperty;
        if (["integer", "float", "monetary"].includes(fieldType) && isSimplePath(c.children[0])) {
            return condition(path, "between", normalizeValue([value1, value2]), false, isProperty);
        }
    }
    return operate(
        rewriteNConsecutiveChildren(_introduceBetweenOperator),
        tree,
        options,
        "connector"
    );
}

/**
 * Expands "Between" operators into standard domain bounds, scoping nested paths with
 * an "any" condition to ensure both bounds apply to the exact same related record.
 * @param {Tree} tree
 * @returns {Tree}
 */
function eliminateBetweenOperators(tree) {
    function _eliminateBetweenOperator(c) {
        if (c.operator !== "between") {
            return;
        }
        const { initialPath, lastPart } = splitPath(c);
        return wrapInAny(
            makeBetween(lastPart, c.value[0], c.value[1], c.isProperty),
            initialPath,
            c.negate
        );
    }
    return operate(_eliminateBetweenOperator, tree);
}

/**
 * Flattens specific "any" operators containing "between" or "in range" conditions by combining their paths
 * @param {Tree} tree
 * @returns {Tree}
 */
function eliminateAnyOperators(tree) {
    function _eliminateAnyOperator(c) {
        if (
            c.operator === "any" &&
            isTree(c.value) &&
            c.value.type === "condition" &&
            typeof c.path === "string" &&
            typeof c.value.path === "string" &&
            !c.negate &&
            !c.value.negate &&
            ["between", "in range"].includes(c.value.operator)
        ) {
            return updateCondition(c.value, { path: `${c.path}.${c.value.path}` });
        }
    }
    return operate(_eliminateAnyOperator, tree);
}

/**
 * Removes explicit TRUE or FALSE leaf conditions by replacing them with equivalent empty connectors.
 * @param {Tree} tree
 * @returns {Tree}
 */
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

/**
 * Applies transformations to introduce virtual operators (e.g., set, starts with, between, in range).
 * @param {Tree} tree
 * @param {TreeOperatorOptions} options
 * @returns {boolean}
 */
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

/**
 * Reverts virtual operators back into their standard domain condition equivalents.
 * @param {Tree} tree
 * @param {TreeOperatorOptions} options
 * @returns {boolean}
 */
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

/**
 * Compares two condition trees for logical equivalence by removing virtual operators and explicit leaves.
 * @param {Tree} tree
 * @param {Tree} otherTree
 * @returns {boolean}
 */
export function areEquivalentTrees(tree, otherTree) {
    const simplifiedTree = removeFalseTrueLeaves(eliminateVirtualOperators(tree));
    const otherSimplifiedTree = removeFalseTrueLeaves(eliminateVirtualOperators(otherTree));
    return areEqualTrees(simplifiedTree, otherSimplifiedTree);
}
