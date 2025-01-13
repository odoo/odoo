import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

class PriceListBoxedOptionPlugin extends Plugin {
    static id = "PriceListBoxedOption";
    resources = {
        builder_options: [
            withSequence(5, {
                template: "html_builder.PriceListBoxedOption",
                selector: ".s_pricelist_boxed",
            }),
            withSequence(5, {
                template: "html_builder.PriceListBoxedSectionOption",
                selector: ".s_pricelist_boxed_section",
            }),
            withSequence(10, {
                template: "html_builder.PriceListBoxedDescriptionOption",
                selector: ".s_pricelist_boxed",
            }),
        ],
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

registry.category("website-plugins").add(PriceListBoxedOptionPlugin.id, PriceListBoxedOptionPlugin);
