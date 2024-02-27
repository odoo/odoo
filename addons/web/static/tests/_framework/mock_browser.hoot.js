import { mockLocation } from "@odoo/hoot-mock";

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * List of properties that should not be mocked on the browser object.
 *
 * This is because they are already handled by HOOT and tampering with them could
 * lead to unexpected behavior.
 */
const READONLY_PROPERTIES = [
    "cancelAnimationFrame",
    "clearInterval",
    "clearTimeout",
    "requestAnimationFrame",
    "setInterval",
    "setTimeout",
];

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * Browser module needs to be mocked to patch the `location` global object since
 * it can't be directly mocked on the window object.
 *
 * @param {string} name
 * @param {OdooModule} module
 */
export function mockBrowserFactory(name, { fn }) {
    return (...args) => {
        const browserModule = fn(...args);
        const properties = {
            location: {
                get: () => mockLocation,
                set: (value) => (mockLocation.href = value),
            },
        };
        for (const property of READONLY_PROPERTIES) {
            const originalValue = browserModule.browser[property];
            properties[property] = {
                configurable: false,
                get: () => originalValue,
            };
        }

        Object.defineProperties(browserModule.browser, properties);

        return browserModule;
    };
}
