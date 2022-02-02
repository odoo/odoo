/** @odoo-module **/

const { blockDom } = owl;

/**
 * loads a template using getTemplate, and render the template immediately;
 *
 * @param {string} template
 * @param {Object} context
 * @returns string: the html of the template
 */

export function renderToString(template, context = {}) {
    const app = renderToString.app;
    if (!app) {
        throw new Error("an app must be configured before using renderToString");
    }
    const templateFn = app.getTemplate(template);
    const bdom = templateFn(context, {});
    const div = document.createElement("div");
    blockDom.mount(bdom, div);
    return div.innerHTML;
}
