/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import options from "@web_editor/js/editor/snippets.options";

options.registry.Pricelist = options.Class.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Show/hide descriptions.
     */
    toggleDescription(previewMode, widgetValue, params) {
        const dishes = this.$target[0].querySelectorAll("." + params.itemsClass);
        let description;

        if (widgetValue) {
            dishes.forEach((el) => {
                description = el.querySelector("." + params.descriptionClass);
                if (description) {
                    description.classList.remove("d-none");
                } else {
                    const descriptionEl = document.createElement("p");
                    descriptionEl.classList.add(
                        params.descriptionClass,
                        "d-block",
                        "mt-2",
                        "pe-5",
                        "text-muted",
                        "o_default_snippet_text"
                    );
                    if (params.descriptionExtraClass) {
                        descriptionEl.classList.add(params.descriptionExtraClass);
                    } else if (this.$target[0].matches(".s_pricelist_boxed, .s_pricelist_cafe")) {
                        // TODO: remove in master where DB will have the class thanks to the XML.
                        descriptionEl.classList.add("o_small")
                    }
                    descriptionEl.textContent = _t("Add a description here");
                    el.appendChild(descriptionEl);
                }
            });
        } else {
            dishes.forEach((el) => {
                description = el.querySelector("." + params.descriptionClass);
                if (description && (description.classList.contains("o_default_snippet_text") || description.querySelector(".o_default_snippet_text"))) {
                    description.remove();
                } else if (description) {
                    description.classList.add("d-none");
                }
            });
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        if (methodName === "toggleDescription") {
            const description = this.$target[0].querySelector("." + params.descriptionClass);
            return description && !description.classList.contains("d-none");
        }
        return this._super(...arguments);
    },
});
