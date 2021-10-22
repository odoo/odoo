/** @odoo-module **/

import { evaluate, formatAST, parseExpr } from "./py_js/py";
import { toPyValue } from "./py_js/py_utils";

/**
 * @typedef {import("./py_js/py_parser").AST} AST
 * @typedef {[string, string, any]} Condition
 * @typedef {("&" | "|" | "!" | Condition)[]} DomainListRepr
 * @typedef {DomainListRepr | string | Domain} DomainRepr
 */

class InvalidDomainError extends Error {}

/**
 * Javascript representation of an Odoo domain
 */
export class Domain {
    /**
     * Combine various domains together with a given operator
     * @param {DomainRepr[]} domains
     * @param {"AND" | "OR"} operator
     * @returns {Domain}
     */
    static combine(domains, operator) {
        if (domains.length === 0) {
            return new Domain([]);
        }
        const domain1 = domains[0] instanceof Domain ? domains[0] : new Domain(domains[0]);
        if (domains.length === 1) {
            return domain1;
        }
        const domain2 = Domain.combine(domains.slice(1), operator);
        const result = new Domain([]);
        const astValues1 = domain1.ast.value;
        const astValues2 = domain2.ast.value;
        const op = operator === "AND" ? "&" : "|";
        const combinedAST = { type: 4 /* List */, value: astValues1.concat(astValues2) };
        result.ast = normalizeDomainAST(combinedAST, op);
        return result;
    }

    /**
     * Combine various domains together with `AND` operator
     * @param {DomainRepr} domains
     * @returns {Domain}
     */
    static and(domains) {
        return Domain.combine(domains, "AND");
    }

    /**
     * Combine various domains together with `OR` operator
     * @param {DomainRepr} domains
     * @returns {Domain}
     */
    static or(domains) {
        return Domain.combine(domains, "OR");
    }

    /**
     * Return the negation of the domain
     * @returns {Domain}
     */
    static not(domain) {
        const result = new Domain(domain);
        result.ast.value.unshift({ type: 1, value: "!" });
        return result;
    }

    /**
     * @param {DomainRepr} [descr]
     */
    constructor(descr = []) {
        if (descr instanceof Domain) {
            /** @type {AST} */
            return new Domain(descr.toString());
        } else {
            const rawAST = typeof descr === "string" ? parseExpr(descr) : toAST(descr);
            this.ast = normalizeDomainAST(rawAST);
        }
    }

    /**
     * Check if the set of records represented by a domain contains a record
     *
     * @param {Object} record
     * @returns {boolean}
     */
    contains(record) {
        const expr = evaluate(this.ast, record);
        return matchDomain(record, expr);
    }

    /**
     * @returns {string}
     */
    toString() {
        return formatAST(this.ast);
    }

    /**
     * @param {Object} context
     * @returns {DomainListRepr}
     */
    toList(context) {
        return evaluate(this.ast, context);
    }
}

const TRUE_LEAF = [1, "=", 1];
const FALSE_LEAF = [0, "=", 1];
const TRUE_DOMAIN = new Domain([TRUE_LEAF]);
const FALSE_DOMAIN = new Domain([FALSE_LEAF]);

Domain.TRUE = TRUE_DOMAIN;
Domain.FALSE = FALSE_DOMAIN;

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

/**
 * @param {DomainListRepr} domain
 * @returns {AST}
 */
function toAST(domain) {
    const elems = domain.map((elem) => {
        switch (elem) {
            case "!":
            case "&":
            case "|":
                return { type: 1 /* String */, value: elem };
            default:
                return {
                    type: 10 /* Tuple */,
                    value: elem.map(toPyValue),
                };
        }
    });
    return { type: 4 /* List */, value: elems };
}

/**
 * Normalizes a domain
 *
 * @param {AST} domain
 * @param {'&' | '|'} [op]
 * @returns {AST}
 */

function normalizeDomainAST(domain, op = "&") {
    if (domain.type !== 4 /* List */) {
        throw new InvalidDomainError("Invalid domain AST");
    }
    if (domain.value.length === 0) {
        return domain;
    }
    let expected = 1;
    for (let child of domain.value) {
        if (child.type === 1 /* String */ && (child.value === "&" || child.value === "|")) {
            expected++;
        } else if (child.type !== 1 /* String */ || child.value !== "!") {
            expected--;
        }
    }
    let values = domain.value.slice();
    while (expected < 0) {
        expected++;
        values.unshift({ type: 1 /* String */, value: op });
    }
    if (expected > 0) {
        throw new InvalidDomainError(
            `invalid domain ${formatAST(domain)} (missing ${expected} segment(s))`
        );
    }
    return { type: 4 /* List */, value: values };
}

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
    const fieldValue = typeof field === "number" ? field : record[field];
    switch (operator) {
        case "=":
        case "==":
            return JSON.stringify(fieldValue) === JSON.stringify(value);
        case "!=":
        case "<>":
            return JSON.stringify(fieldValue) !== JSON.stringify(value);
        case "<":
            return fieldValue < value;
        case "<=":
            return fieldValue <= value;
        case ">":
            return fieldValue > value;
        case ">=":
            return fieldValue >= value;
        case "in": {
            const val = Array.isArray(value) ? value : [value];
            const fieldVal = Array.isArray(fieldValue) ? fieldValue : [fieldValue];
            return fieldVal.some((fv) => val.includes(fv));
        }
        case "not in": {
            const val = Array.isArray(value) ? value : [value];
            const fieldVal = Array.isArray(fieldValue) ? fieldValue : [fieldValue];
            return !fieldVal.some((fv) => val.includes(fv));
        }
        case "like":
            if (fieldValue === false) {
                return false;
            }
            return fieldValue.indexOf(value) >= 0;
        case "=like":
            if (fieldValue === false) {
                return false;
            }
            return new RegExp(value.replace(/%/g, ".*")).test(fieldValue);
        case "ilike":
            if (fieldValue === false) {
                return false;
            }
            return fieldValue.toLowerCase().indexOf(value.toLowerCase()) >= 0;
        case "=ilike":
            if (fieldValue === false) {
                return false;
            }
            return new RegExp(value.replace(/%/g, ".*"), "i").test(fieldValue);
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
        if (item in operators) {
            const operator = operators[item];
            const operands = condStack.splice(-operator.length);
            condStack.push(operator(...operands));
        } else {
            condStack.push(item);
        }
    }
    return matchCondition(record, condStack.pop());
}
