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
 * @param {OdooModule} module
 */
export function makeTemplateFactory(name, module) {
    return () => {
        if (!loader.modules.has(name)) {
            const factory = module.fn;
            module.fn = (...args) => {
                const exports = factory(...args);

                exports.registerTemplateProcessor(replaceAttributes);

                return exports;
            };
            loader.startModule(name);
        }
        return loader.modules.get(name);
    };
}
