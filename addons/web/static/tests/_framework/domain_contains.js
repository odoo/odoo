import { Domain, InvalidDomainError } from "@web/core/domain";
import { evaluate } from "@web/core/py_js/py";
import { shallowEqual } from "@web/core/utils/arrays";
import { escapeRegExp } from "@web/core/utils/strings";

/** @typedef {import("@web/core/domain").DomainRepr} DomainRepr */

/**
 * @param {Object} record
 * @param {Condition | boolean} condition
 * @returns {boolean}
 */
function matchCondition(record, condition) {
    if (typeof condition === "boolean") {
        return condition;
    }
    const [field, operator, value] = condition;

    if (typeof field === "string") {
        const names = field.split(".");
        if (names.length >= 2) {
            return matchCondition(record[names[0]], [names.slice(1).join("."), operator, value]);
        }
    }
    let likeRegexp, ilikeRegexp;
    if (["like", "not like", "ilike", "not ilike"].includes(operator)) {
        likeRegexp = new RegExp(`(.*)${escapeRegExp(value).replaceAll("%", "(.*)")}(.*)`, "g");
        ilikeRegexp = new RegExp(`(.*)${escapeRegExp(value).replaceAll("%", "(.*)")}(.*)`, "gi");
    }
    const fieldValue = typeof field === "number" ? field : record[field];
    const isNot = operator.startsWith("not ");
    switch (operator) {
        case "=?":
            if ([false, null].includes(value)) {
                return true;
            }
        // eslint-disable-next-line no-fallthrough
        case "=":
        case "==":
            if (Array.isArray(fieldValue) && Array.isArray(value)) {
                return shallowEqual(fieldValue, value);
            }
            return fieldValue === value;
        case "!=":
        case "<>":
            return !matchCondition(record, [field, "=", value]);
        case "<":
            return fieldValue < value;
        case "<=":
            return fieldValue <= value;
        case ">":
            return fieldValue > value;
        case ">=":
            return fieldValue >= value;
        case "in":
        case "not in": {
            const val = Array.isArray(value) ? value : [value];
            const fieldVal = Array.isArray(fieldValue) ? fieldValue : [fieldValue];
            return Boolean(fieldVal.some((fv) => val.includes(fv))) != isNot;
        }
        case "like":
        case "not like":
            if (fieldValue === false) {
                return isNot;
            }
            return Boolean(fieldValue.match(likeRegexp)) != isNot;
        case "=like":
        case "not =like":
            if (fieldValue === false) {
                return isNot;
            }
            return (
                Boolean(new RegExp(escapeRegExp(value).replace(/%/g, ".*")).test(fieldValue)) !=
                isNot
            );
        case "ilike":
        case "not ilike":
            if (fieldValue === false) {
                return isNot;
            }
            return Boolean(fieldValue.match(ilikeRegexp)) != isNot;
        case "=ilike":
        case "not =ilike":
            if (fieldValue === false) {
                return isNot;
            }
            return (
                Boolean(
                    new RegExp(escapeRegExp(value).replace(/%/g, ".*"), "i").test(fieldValue)
                ) != isNot
            );
        case "any":
        case "not any":
        case "child_of":
        case "parent_of":
            return true;
    }
    throw new InvalidDomainError("could not match domain");
}

/**
 * @param {Object} record
 * @returns {Object}
 */
function makeOperators(record) {
    const match = matchCondition.bind(null, record);
    return {
        "!": (x) => !match(x),
        "&": (a, b) => match(a) && match(b),
        "|": (a, b) => match(a) || match(b),
    };
}

/**
 *
 * @param {Object} record
 * @param {DomainListRepr} domain
 * @returns {boolean}
 */
function matchDomain(record, domain) {
    if (domain.length === 0) {
        return true;
    }
    const operators = makeOperators(record);
    const reversedDomain = Array.from(domain).reverse();
    const condStack = [];
    for (const item of reversedDomain) {
        const operator = typeof item === "string" && operators[item];
        if (operator) {
            const operands = condStack.splice(-operator.length);
            condStack.push(operator(...operands));
        } else {
            condStack.push(item);
        }
    }
    return matchCondition(record, condStack.pop());
}

/**
 * Check if the set of records represented by a domain contains a record
 * Warning: smart dates (see parseSmartDateInput) are not handled here.
 *
 * @param {DomainRepr} domain
 * @param {Object} record
 * @returns {boolean}
 */
export function contains(domain, record) {
    domain = new Domain(domain);
    const expr = evaluate(domain.ast, record);
    return matchDomain(record, expr);
}
