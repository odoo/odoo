/** @odoo-module */

/**
 * @typedef {import("./core/runner").Runner} Runner
 */

/** @type {Runner | null} */
let currentMainRunner = null;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {string} funcName
 */
export function ensureTest(funcName) {
    if (!mainRunner()?.getCurrent().test) {
        throw new Error(`Cannot call '${funcName}' from outside a test`);
    }
}

export function mainRunner() {
    return currentMainRunner;
}

/**
 * @param {Runner} runner
 */
export function setMainRunner(runner) {
    currentMainRunner = runner;
}
