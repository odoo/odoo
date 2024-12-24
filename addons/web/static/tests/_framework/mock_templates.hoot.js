// ! WARNING: this module cannot depend on modules not ending with ".hoot" (except libs) !

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * We remove all the attributes `src` and `alt` from the template and replace them by
 * data attributes (e.g. `src` to `data-src`, `alt` to `data-alt`).
 * alt attribute causes issues with scroll tests. Indeed, alt is
 * displayed between the time we scroll programmatically and the time
 * we assert for the scroll position. The src attribute is removed
 * as well to make sure images won't trigger a GET request on the
 * server.
 *
 * @param {Element} template
 */
const replaceAttributes = (template) => {
    for (const { attribute, tagName, value } of ATTRIBUTE_DEFAULT_VALUES) {
        for (const prefix of ATTRIBUTE_PREFIXES) {
            const fullAttribute = `${prefix}${attribute}`;
            const dataAttribute = `${prefix}data-${attribute}`;
            for (const element of template.querySelectorAll(`${tagName || ""}[${fullAttribute}]`)) {
                element.setAttribute(dataAttribute, element.getAttribute(fullAttribute));
                if (attribute !== fullAttribute) {
                    element.removeAttribute(fullAttribute);
                }
                element.setAttribute(attribute, value);
            }
        }
    }
};

const ATTRIBUTE_DEFAULT_VALUES = [
    // "alt": empty string
    { attribute: "alt", value: "" },
    { attribute: "src", tagName: "iframe", value: "" },
    {
        attribute: "src",
        tagName: "img",
        // "src": 1x1 fuschia image
        value: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z9DwHwAGBQKA3H7sNwAAAABJRU5ErkJggg==",
    },
];
const ATTRIBUTE_PREFIXES = ["", "t-att-", "t-attf-"];

const { loader } = odoo;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {string} name
 * @param {OdooModuleFactory} factory
 */
export function makeTemplateFactory(name, factory) {
    return () => {
        if (loader.modules.has(name)) {
            return loader.modules.get(name);
        }

        /** @type {Map<string, function>} */
        const compiledTemplates = new Map();

        const factoryFn = factory.fn;
        factory.fn = (...args) => {
            const exports = factoryFn(...args);
            const { clearProcessedTemplates, getTemplate } = exports;

            // Patch "getTemplates" to access local cache
            exports.getTemplate = function mockedGetTemplate(name) {
                if (!this) {
                    // Used outside of Owl.
                    return getTemplate(name);
                }
                const rawTemplate = getTemplate(name) || this.rawTemplates[name];
                if (typeof rawTemplate === "function" && !(rawTemplate instanceof Element)) {
                    return rawTemplate;
                }
                if (!compiledTemplates.has(rawTemplate)) {
                    compiledTemplates.set(rawTemplate, this._compileTemplate(name, rawTemplate));
                }
                return compiledTemplates.get(rawTemplate);
            };

            // Patch "clearProcessedTemplates" to clear local template cache
            exports.clearProcessedTemplates = function mockedClearProcessedTemplates() {
                compiledTemplates.clear();
                return clearProcessedTemplates(...arguments);
            };

            // Replace alt & src attributes by default on all templates
            exports.registerTemplateProcessor(replaceAttributes);

            return exports;
        };

        return loader.startModule(name);
    };
}
