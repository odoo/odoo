//-----------------------------------------------------------------------------
// ! PRODUCTION CODE: DO NOT TOUCH
//-----------------------------------------------------------------------------

/**
 * @todo add runtime type checking
 * @param {number} a
 * @param {number} b
 * @returns {number}
 */
export function add(a, b) {
    return a + b;
}

/**
 * @template A, B
 * @param {Iterable<A>} a
 * @param {Iterable<B>} b
 * @returns {(A | B)[]}
 */
export function concatenate(a, b) {
    if (!a?.[Symbol.iterator] || !b?.[Symbol.iterator]) {
        throw new Error("Cannot concatenate non-iterable objects");
    }
    return [...a, ...b];
}
