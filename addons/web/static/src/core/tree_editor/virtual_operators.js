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
    if (isSimpleAnd(c)) {
        const [
            { path: p1, operator: op1, value: value1 },
            { path: p2, operator: op2, value: value2 },
        ] = c.children;
        if (p1 === p2 && op1 === ">=" && op2 === "<=") {
            return { path: p1, value1, value2 };
        }
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
    if (isSimpleAnd(c)) {
        const [
            { path: p1, operator: op1, value: value1 },
            { path: p2, operator: op2, value: value2 },
        ] = c.children;
        if (p1 === p2 && op1 === ">=" && op2 === "<") {
            return { path: p1, value1, value2 };
        }
    }
    return false;
}

function makeStrictBetween(path, value1, value2, isProperty) {
    return connector("&", [
        condition(path, ">=", value1, false, isProperty),
        condition(path, "<", value2, false, isProperty),
    ]);
}

function boundDate(delta) {
    if (!delta) {
        return expression(`context_today().strftime("%Y-%m-%d")`);
    }
    return expression(`(context_today() + relativedelta(${delta})).strftime('%Y-%m-%d')`);
}

function boundDatetime(delta) {
    if (!delta) {
        return expression(
            `datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
        );
    }
    return expression(
        `datetime.datetime.combine(context_today() + relativedelta(${delta}), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
    );
}

const BOUNDS_SMART_DATES = [
    ["today", "today", "today +1d"],
    ["last 7 days", "today -7d", "today"],
    ["last 30 days", "today -30d", "today"],
    ["month to date", "today =1d", "today +1d"],
    ["last month", "today =1d -1m", "today =1d"],
    ["year to date", "today =1m =1d", "today +1d"],
    ["last 12 months", "today =1d -12m", "today =1d"],
];
const DELTAS = [
    ["today", "", "days = 1"],
    ["last 7 days", "days = -7", ""],
    ["last 30 days", "days = -30", ""],
    ["month to date", "day = 1", "days = 1"],
    ["last month", "day = 1, months = -1", "day = 1"],
    ["year to date", "day = 1, month = 1", "days = 1"],
    ["last 12 months", "day = 1, months = -12", "day = 1"],
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
        const res1 = isStrictBetween(c);
        if (res1) {
            const generateSmartDates =
                "generateSmartDates" in options ? options.generateSmartDates : true;
            // @ts-ignore
            const { path, value1, value2 } = res1;
            const fieldDef = options.getFieldDef?.(path);
            const fieldType = fieldDef?.type;
            const isProperty = fieldDef?.is_property;
            if (["date", "datetime"].includes(fieldType) && isSimplePath(path, isProperty)) {
                const bounds = getBounds(generateSmartDates, fieldType);
                for (const [valueType, leftBound, rightBound] of bounds) {
                    if (
                        generateSmartDates
                            ? value1 === leftBound && value2 === rightBound
                            : value1._expr === leftBound._expr && value2._expr === rightBound._expr
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
        }
        const res2 = isBetween(c);
        if (res2) {
            // @ts-ignore
            const { path, value1, value2 } = res2;
            const fieldDef = options.getFieldDef?.(path);
            const fieldType = fieldDef?.type;
            const isProperty = fieldDef?.is_property;
            if (["date", "datetime"].includes(fieldType) && isSimplePath(path, isProperty)) {
                return condition(
                    path,
                    "in range",
                    [
                        fieldType,
                        "custom range",
                        // @ts-ignore
                        ...normalizeValue([value1, value2]),
                    ],
                    false,
                    isProperty
                );
            }
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
        let tree;
        if (valueType === "custom range") {
            tree = makeBetween(lastPart, value1, value2, isProperty);
        } else {
            const generateSmartDates =
                "generateSmartDates" in options ? options.generateSmartDates : true;
            const bounds = getBounds(generateSmartDates, fieldType);
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
