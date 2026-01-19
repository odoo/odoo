export const resourceSequenceSymbol = Symbol("resourceSequence");

/**
 * Sequence marker used with `withSequence` to ensure the wrapped handler
 * runs before other handlers of the same resource.
 *
 * Intended for DOM read logic so it executes before potential DOM mutations,
 * avoiding layout thrashing.
 */
export const READ = 0;

/**
 * @template T
 * @typedef {Object} ResourceWithSequence
 * @property {T} object
 */

/**
 * @template T
 * @param {number} sequenceNumber
 * @param {T} object
 * @returns {ResourceWithSequence<T>}
 */
export function withSequence(sequenceNumber, object) {
    if (typeof sequenceNumber !== "number") {
        throw new Error(
            `sequenceNumber must be a number. Got ${sequenceNumber} (${typeof sequenceNumber}).`
        );
    }
    return {
        [resourceSequenceSymbol]: sequenceNumber,
        object,
    };
}

export function warnOfNamingConvention(
    functionName,
    resourceId,
    { prefix, suffix, targetFunction }
) {
    const styles = ["color: red;", "color: default;", "color: grey;"];
    let message = "";
    if (targetFunction) {
        message = `naming suggests the resource \`${resourceId}\` should use \`editor.${targetFunction}\`.`;
    } else if (prefix || suffix) {
        message = `resources called with \`${functionName}\` should `;
        if (prefix) {
            message += `start with "${prefix}_"${suffix ? " and " : "."}`;
        }
        if (suffix) {
            message += `end with "_${suffix}".`;
        }
    }
    console.warn(
        `%c[EDITOR]%c Warning: ${message}\n%cRegarding: \`${functionName}("${resourceId}")\``,
        ...styles
    );
}
