import { _t } from "@web/core/l10n/translation";
import { App, Component } from "@odoo/owl";
import { getTemplate } from "@web/core/templates";
import { UrlAutoComplete } from "@website/components/autocomplete_with_pages/url_autocomplete";
import weUtils from "@web_editor/js/common/utils";

/**
 * Allows the given input to propose existing website URLs.
 *
 * @param {HTMLInputElement} input
 */
function autocompleteWithPages(input, options= {}) {
    const owlApp = new App(UrlAutoComplete, {
        env: Component.env,
        dev: Component.env.debug,
        getTemplate,
        props: {
            options,
            loadAnchors: weUtils.loadAnchors,
            targetDropdown: input,
        },
        translatableAttributes: ["data-tooltip"],
        translateFn: _t,
    });

    const container = document.createElement("div");
    container.classList.add("ui-widget", "ui-autocomplete", "ui-widget-content", "border-0");
    document.body.appendChild(container);
    owlApp.mount(container)
    return () => {
        owlApp.destroy();
        container.remove();
    }
}

export default {
    autocompleteWithPages: autocompleteWithPages,
};
