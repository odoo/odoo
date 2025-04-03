import { App, blockDom, Component } from "@odoo/owl";
import { getTemplate } from "@web/core/templates";
import { _t } from "@web/core/l10n/translation";
import { getInnerHtml } from "@web/core/utils/html";

export function renderToElement(template, context = {}) {
    const el = render(template, context).firstElementChild;
    if (el?.nextElementSibling) {
        throw new Error(
            `The rendered template '${template}' contains multiple root ` +
                `nodes that will be ignored using renderToElement, you should ` +
                `consider using renderToFragment or refactoring the template.`
        );
    }
    el?.remove();
    return el;
}

export function renderToFragment(template, context = {}) {
    const frag = document.createDocumentFragment();
    for (const el of [...render(template, context).children]) {
        frag.appendChild(el);
    }
    return frag;
}

/**
 * renders a template with an (optional) context and outputs it as a string
 *
 * @deprecated use renderToMarkup instead, as HTML string should always be stored in a markup
 * @param {string} template
 * @param {Object} context
 * @returns string: the html of the template
 */
export function renderToString(template, context = {}) {
    return renderToMarkup(template, context).toString();
}
let app;
Object.defineProperty(renderToString, "app", {
    get: () => {
        if (!app) {
            app = new App(Component, {
                name: "renderToString",
                getTemplate,
                translatableAttributes: ["data-tooltip"],
                translateFn: _t,
            });
        }
        return app;
    },
});

function render(template, context = {}) {
    const app = renderToString.app;
    const templateFn = app.getTemplate(template);
    const bdom = templateFn(context, {});
    const div = document.createElement("div");
    blockDom.mount(bdom, div);
    return div;
}

/**
 * renders a template with an (optional) context and returns a Markup string,
 * suitable to be inserted in a template with a t-out directive
 *
 * @param {string} template
 * @param {Object} context
 * @returns {ReturnType<markup>} the html of the template, as a markup string
 */
export function renderToMarkup(template, context = {}) {
    return getInnerHtml(render(template, context));
}
