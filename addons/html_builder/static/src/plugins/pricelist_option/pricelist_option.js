import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

import { defaultBuilderComponents } from "../../core/default_builder_components";

export class AddProductButton extends Component {
    static template = "html_builder.AddProductButton";
    static components = { ...defaultBuilderComponents };
    static props = {
        applyTo: String,
        productSelector: String,
    };
}
class PriceListOptionPlugin extends Plugin {
    static id = "PriceListOptionPlugin";
    resources = {
        builder_actions: this.getActions(),
    };

    getActions() {
        return {
            togglePriceListDescription: {
                isApplied: ({ editingElement, param }) => {
                    const description = editingElement.querySelector(`.${param.descriptionClass}`);
                    return description && !description.classList.contains("d-none");
                },
                apply: ({ editingElement, param }) => {
                    const items = editingElement.querySelectorAll(`.${param.itemClass}`);
                    for (const item of items) {
                        const description = item.querySelector("." + param.descriptionClass);
                        if (description) {
                            description.classList.remove("d-none");
                        } else {
                            const descriptionEl = this.document.createElement("p");
                            descriptionEl.classList.add(
                                param.descriptionClass,
                                "d-block",
                                "pe-5",
                                "text-muted"
                            );
                            descriptionEl.textContent = _t("Add a description here");
                            item.appendChild(descriptionEl);
                        }
                    }
                },
                clean: ({ editingElement, param }) => {
                    const items = editingElement.querySelectorAll(`.${param.itemClass}`);
                    for (const item of items) {
                        const description = item.querySelector("." + param.descriptionClass);
                        if (description) {
                            description.classList.add("d-none");
                        }
                    }
                },
            },
        };
    }
}

registry.category("website-plugins").add(PriceListOptionPlugin.id, PriceListOptionPlugin);
