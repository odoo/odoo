/**
 * Builds a simplified representation of an object, managing complex structures and circular references up to a defined maximum depth.
 * This function is useful for visualizing objects that would otherwise cause errors when converting to a string, such as using `JSON.stringify`
 * on circular structures.
 *
 * @param {Object} obj - The object to represent. Can be a literal object or an array.
 * @param {number} [depth=0] - The current depth of recursive iteration. Defaults to 0.
 * @param {number} [maxDepth=2] - The maximum depth to which the object should be explored. Beyond this depth, objects are not further decomposed.
 * @returns {Object|Array} A simplified representation of the initial object, with nested objects represented up to the specified maximum depth.
 */
function buildRepresentativeObject(obj, depth = 0, maxDepth = 2) {
    if (depth > maxDepth || obj === null || typeof obj !== "object") {
        return obj;
    }
    const result = Array.isArray(obj) ? [] : {};
    for (const key in obj) {
        if (Object.hasOwn(obj, key)) {
            try {
                const value = obj[key];
                if (typeof value === "object" && value !== null) {
                    result[key] = buildRepresentativeObject(value, depth + 1, maxDepth);
                } else {
                    result[key] = value;
                }
            } catch (error) {
                result[key] = `Error: ${error.message}`;
            }
        }
    }
    return result;
}

/**
 * Logs a simplified representation of an object to the console, using `buildRepresentativeObject` to manage complex structures and circular
 * references up to a defined maximum depth.
 * This function is useful for debugging purposes, where directly logging complex objects can be impractical or lead to errors, such as
 * with circular structures.
 *
 * @param {Object} obj - The object to log. Can be a literal object, an array, or any other type that can be represented as an object.
 * @param {number} [depth=0] - The current depth of recursive iteration when building the representative object. Defaults to 0.
 * @param {number} [maxDepth=2] - The maximum depth to which the object should be explored when building the representative object. Beyond this depth, objects are not further decomposed.
 * @returns {void} This function does not return a value; it logs output to the console.
 */
function log(obj, depth = 0, maxDepth = 2) {
    return console.log(buildRepresentativeObject(obj, depth, maxDepth));
}

/**
 * Compares two objects recursively to identify differences between them, handling circular references and limiting comparison depth.
 * This function is particularly useful in debugging scenarios where identifying changes between two states of an object is necessary.
 *
 * @param {Object} obj1 - The first object to compare.
 * @param {Object} obj2 - The second object to compare, ideally representing a later state of the first object to identify changes.
 * @param {Map} [visited=new Map()] - An internal parameter used to track visited objects and manage circular references. It should not be set or modified externally.
 * @param {number} [depth=0] - The current depth of the comparison recursion. Used internally to limit the comparison to a certain depth.
 * @param {number} [maxDepth=10] - The maximum depth to which the comparison should be performed to prevent excessively deep recursion.
 * @returns {Object} An object representing the differences between `obj1` and `obj2`. If objects are identical, an empty object is returned. If a circular reference or maximum depth limit is reached, an error message is included in the return object.
 *
 * @example
 * // Assume `this.pos.getOrder()` returns an order object with its current state.
 * // Capture the state of the order before a certain operation.
 * const beforeBooking = buildRepresentativeObject(this.pos.getOrder());
 * // Perform an operation that modifies the order.
 * this.pos.getOrder().setBooked(true);
 * // Capture the state of the order after the operation.
 * const afterBooking = buildRepresentativeObject(this.pos.getOrder());
 * // Compare the before and after states to see what has changed.
 * console.log("Differences: ", compareObjects(beforeBooking, afterBooking));
 */
function compareObjects(obj1, obj2, visited = new Map(), depth = 0, maxDepth = 10) {
    if (depth > maxDepth) {
        return { error: "Profondeur de comparaison maximale atteinte." };
    }
    if (visited.has(obj1) || visited.has(obj2)) {
        return visited.get(obj1) === visited.get(obj2)
            ? {}
            : { error: "Référence circulaire détectée." };
    }
    visited.set(obj1, depth);
    visited.set(obj2, depth);
    const differences = {};
    const allKeys = new Set([...Object.keys(obj1), ...Object.keys(obj2)]);
    allKeys.forEach((key) => {
        const val1 = obj1[key];
        const val2 = obj2[key];
        if (typeof val1 !== typeof val2 || val1 !== val2) {
            if (val1 && val2 && typeof val1 === "object" && typeof val2 === "object") {
                const subDiff = compareObjects(val1, val2, visited, depth + 1, maxDepth);
                if (Object.keys(subDiff).length > 0) {
                    differences[key] = subDiff;
                }
            } else {
                differences[key] = { obj1: val1, obj2: val2 };
            }
        }
    });
    return buildRepresentativeObject(differences);
}

export const debug = {
    compareObjects,
    buildRepresentativeObject,
    log,
};
