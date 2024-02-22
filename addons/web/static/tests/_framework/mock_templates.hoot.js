const { loader } = odoo;

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
    for (const attributeName of ["alt", "src"]) {
        for (const prefix of ["", "t-att-", "t-attf-"]) {
            const fullAttribute = `${prefix}${attributeName}`;
            const dataAttribute = `${prefix}data-${attributeName}`;
            for (const element of template.querySelectorAll(`[${fullAttribute}]`)) {
                element.setAttribute(dataAttribute, element.getAttribute(fullAttribute));
                element.removeAttribute(fullAttribute);
            }
        }
    }
};

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
