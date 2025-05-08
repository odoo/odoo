import { evaluate, formatAST, parseExpr } from "./py_js/py";
import { toPyValue } from "./py_js/py_utils";

/**
 * @typedef {import("./py_js/py_parser").AST} AST
 * @typedef {[string | 0 | 1, string, any]} Condition
 * @typedef {("&" | "|" | "!" | Condition)[]} DomainListRepr
 * @typedef {DomainListRepr | string | Domain} DomainRepr
 */

export class InvalidDomainError extends Error {}

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
     * Return a new domain with `neutralized` leaves (for the leaves that are applied on the field that are part of
     * keysToRemove).
     * @param {DomainRepr} domain
     * @param {string[]} keysToRemove
     * @return {Domain}
     */
    static removeDomainLeaves(domain, keysToRemove) {
        function processLeaf(elements, idx, operatorCtx, newDomain) {
            const leaf = elements[idx];
            if (leaf.type === 10) {
                if (keysToRemove.includes(leaf.value[0].value)) {
                    if (operatorCtx === "&") {
                        newDomain.ast.value.push(...Domain.TRUE.ast.value);
                    } else if (operatorCtx === "|") {
                        newDomain.ast.value.push(...Domain.FALSE.ast.value);
                    }
                } else {
                    newDomain.ast.value.push(leaf);
                }
                return 1;
            } else if (leaf.type === 1) {
                // Special case to avoid OR ('|') that can never resolve to true
                if (
                    leaf.value === "|" &&
                    elements[idx + 1].type === 10 &&
                    elements[idx + 2].type === 10 &&
                    keysToRemove.includes(elements[idx + 1].value[0].value) &&
                    keysToRemove.includes(elements[idx + 2].value[0].value)
                ) {
                    newDomain.ast.value.push(...Domain.TRUE.ast.value);
                    return 3;
                }
                newDomain.ast.value.push(leaf);
                if (leaf.value === "!") {
                    return 1 + processLeaf(elements, idx + 1, "&", newDomain);
                }
                const firstLeafSkip = processLeaf(elements, idx + 1, leaf.value, newDomain);
                const secondLeafSkip = processLeaf(
                    elements,
                    idx + 1 + firstLeafSkip,
                    leaf.value,
                    newDomain
                );
                return 1 + firstLeafSkip + secondLeafSkip;
            }
            return 0;
        }

        domain = new Domain(domain);
        if (domain.ast.value.length === 0) {
            return domain;
        }
        const newDomain = new Domain([]);
        processLeaf(domain.ast.value, 0, "&", newDomain);
        return newDomain;
    }

    /**
     * @param {DomainRepr} [descr]
     */
    constructor(descr = []) {
        if (descr instanceof Domain) {
            /** @type {AST} */
            return new Domain(descr.toString());
        } else {
            let rawAST;
            try {
                rawAST = typeof descr === "string" ? parseExpr(descr) : toAST(descr);
            } catch (error) {
                throw new InvalidDomainError(`Invalid domain representation: ${descr.toString()}`, {
                    cause: error,
                });
            }
            this.ast = normalizeDomainAST(rawAST);
        }
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

    /**
     * Converts the domain into a human-readable format for JSON representation.
     * If the domain does not contain any contextual value, it is converted to a list.
     * Otherwise, it is returned as a string.
     *
     * The string format is less readable due to escaped double quotes.
     * Example: "[\"&\",[\"user_id\",\"=\",uid],[\"team_id\",\"!=\",false]]"
     * @returns {DomainListRepr | string}
     */
    toJson() {
        try {
            // Attempt to evaluate the domain without context
            const evaluatedAsList = this.toList({});
            const evaluatedDomain = new Domain(evaluatedAsList);
            if (evaluatedDomain.toString() === this.toString()) {
                return evaluatedAsList;
            }
            return this.toString();
        } catch {
            // The domain couldn't be evaluated due to contextual values
            return this.toString();
        }
    }
}

/** @type {Condition} */
const TRUE_LEAF = [1, "=", 1];
/** @type {Condition} */
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
        if (domain.type === 10 /* Tuple */) {
            const value = domain.value;
            /* Tuple contains at least one Tuple and optionally string */
            if (
                value.findIndex((e) => e.type === 10) === -1 ||
                !value.every((e) => e.type === 10 || e.type === 1)
            ) {
                throw new InvalidDomainError("Invalid domain AST");
            }
        } else {
            throw new InvalidDomainError("Invalid domain AST");
        }
    }
    if (domain.value.length === 0) {
        return domain;
    }
    let expected = 1;
    for (const child of domain.value) {
        switch (child.type) {
            case 1 /* String */:
                if (child.value === "&" || child.value === "|") {
                    expected++;
                } else if (child.value !== "!") {
                    throw new InvalidDomainError("Invalid domain AST");
                }
                break;
            case 4: /* list */
            case 10 /* tuple */:
                if (child.value.length === 3) {
                    expected--;
                    break;
                }
                throw new InvalidDomainError("Invalid domain AST");
            default:
                throw new InvalidDomainError("Invalid domain AST");
        }
    }
    const values = domain.value.slice();
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
