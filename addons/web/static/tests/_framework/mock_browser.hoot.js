// ! WARNING: this module cannot depend on modules not ending with ".hoot" (except libs) !

import { beforeEach } from "@odoo/hoot";
import { on } from "@odoo/hoot-dom";
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

const anchorHrefDescriptor = Object.getOwnPropertyDescriptor(HTMLAnchorElement.prototype, "href");

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

        beforeEach(function mockAnchorHref() {
            Object.defineProperty(HTMLAnchorElement.prototype, "href", {
                ...anchorHrefDescriptor,
                get() {
                    return this.hasAttribute("href") ? new URL(this.getAttribute("href")).href : "";
                },
            });

            const offHrefClick = on(window, "click", (ev) => {
                const href = ev.target.closest("a[href]")?.href;
                if (!href || ev.defaultPrevented) {
                    return;
                }

                ev.preventDefault();

                // Assign href to mock location instead of actual location
                mockLocation.href = href;

                // Scroll to the target element if the href is/has a hash
                const hash = href.startsWith("#") ? href : new URL(href).hash;
                if (hash) {
                    document.getElementById(hash.slice(1))?.scrollIntoView();
                }
            });

            return function restoreAnchorHref() {
                offHrefClick();
                Object.defineProperty(HTMLAnchorElement.prototype, "href", anchorHrefDescriptor);
            };
        });

        return browserModule;
    };
}
