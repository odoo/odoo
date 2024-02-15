import { mockLocation } from "@odoo/hoot-mock";

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
        Object.defineProperty(browserModule.browser, "location", {
            set(value) {
                mockLocation.href = value;
            },
            get() {
                return mockLocation;
            },
        });
        return browserModule;
    };
}
