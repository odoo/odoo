export function fail(errorMessage) {
    throw new Error(errorMessage);
}

export function assert(current, expected, info) {
    if (current !== expected) {
        fail(`${info}: "${current}" instead of "${expected}".`);
    }
}
