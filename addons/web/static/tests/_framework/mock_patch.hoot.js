// ! WARNING: this module cannot depend on modules not ending with ".hoot" (except libs) !

import { after } from "@odoo/hoot";

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {string} name
 * @param {OdooModuleFactory} factory
 */
export function mockPatchFactory(name, { fn }) {
    return function mockPatch(...args) {
        const patchModule = fn(...args);

        const originalPatch = patchModule.patch;
        patchModule.patch = function patchWithCleanup(obj, patchValue) {
            const unpatch = originalPatch(obj, patchValue);
            after(unpatch);
            return unpatch;
        };

        return patchModule;
    };
}
