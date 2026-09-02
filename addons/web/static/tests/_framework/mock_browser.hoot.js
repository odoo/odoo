// ! WARNING: this module cannot depend on modules not ending with ".hoot" (except libs) !

import { mockLocation } from "@odoo/hoot";

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * Browser module needs to be mocked to patch the `location` global object since
 * it can't be directly mocked on the window object.
 *
 * @param {string} name
 * @param {OdooModuleFactory} factory
 */
export function mockBrowserFactory(name, { fn }) {
    return function mockBrowser(...args) {
        const browserModule = fn(...args);
        browserModule.location = mockLocation;
        return browserModule;
    };
}
