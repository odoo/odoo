// ! WARNING: this module cannot depend on modules not ending with ".hoot" (except libs) !

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * We remove all the `src` attributes (and derived forms) from the template and
 * replace them by data attributes (e.g. `src` to `data-src`, `t-att-src` to
 * `t-att-data-src`). This is done to ensure images will not trigger an actual request
 * on the server.
 *
 * @param {Element} template
 */
const replaceAttributes = (template) => {
    for (const [tagName, value] of SRC_REPLACERS) {
        for (const prefix of ATTRIBUTE_PREFIXES) {
            const targetAttribute = `${prefix}src`;
            const dataAttribute = `${prefix}data-src`;
            for (const element of template.querySelectorAll(`${tagName}[${targetAttribute}]`)) {
                element.setAttribute(dataAttribute, element.getAttribute(targetAttribute));
                if (prefix) {
                    element.removeAttribute(targetAttribute);
                }
                element.setAttribute("src", value);
            }
        }
    }
};

const ONE_FUSCHIA_PIXEL_IMG =
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z9DwHwAGBQKA3H7sNwAAAABJRU5ErkJggg==";

const SRC_REPLACERS = [
    ["iframe", ""],
    ["img", ONE_FUSCHIA_PIXEL_IMG],
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
