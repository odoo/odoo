import { before } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

const migrateCallbacks = {};

export function migrate(container, env) {
    for (const callback of Object.values(migrateCallbacks)) {
        callback(container, env);
    }
}

/**
 * @param {Array} callbacks
 */
export function setupMigrateFunctions(callbacks) {
    before(() => {
        const newCallbacks = {};
        for (let i = 0; i < callbacks.length; i++) {
            newCallbacks[i] = callbacks[i];
        }
        patchWithCleanup(migrateCallbacks, newCallbacks);
    });
}
