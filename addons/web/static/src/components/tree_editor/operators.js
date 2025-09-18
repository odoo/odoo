// @ts-check

/** @module @web/components/tree_editor/operators - Operator negation maps and comparator constants for domain/expression trees */

/** @type {Record<string, string>} Maps each domain operator to its logical negation */
export const TERM_OPERATORS_NEGATION = {
    "<": ">=",
    ">": "<=",
    "<=": ">",
    ">=": "<",
    "=": "!=",
    "!=": "=",
    in: "not in",
    like: "not like",
    ilike: "not ilike",
    "not in": "in",
    "not like": "like",
    "not ilike": "ilike",
};

/** @type {Record<string, string>} Extended negation map including Python identity/equality operators */
export const TERM_OPERATORS_NEGATION_EXTENDED = {
    ...TERM_OPERATORS_NEGATION,
    is: "is not",
    "is not": "is",
    "==": "!=",
    "!=": "==", // override here
};

/** @type {string[]} All comparison operators valid in Python expressions */
export const COMPARATORS = [
    "<",
    "<=",
    ">",
    ">=",
    "in",
    "not in",
    "==",
    "is",
    "!=",
    "is not",
];
