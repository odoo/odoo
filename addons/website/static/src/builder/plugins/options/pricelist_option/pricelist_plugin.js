import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

class PriceListPlugin extends Plugin {
    static id = "priceListPlugin";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            TogglePriceListDescriptionAction,
        },
    };
}

export class TogglePriceListDescriptionAction extends BuilderAction {
    static id = "togglePriceListDescription";
    isApplied({ editingElement, params }) {
        const description = editingElement.querySelector(`.${params.descriptionClass}`);
        return description && !description.classList.contains("d-none");
    }
    apply({ editingElement, params }) {
        const items = editingElement.querySelectorAll(`.${params.itemClass}`);
        for (const item of items) {
            const description = item.querySelector("." + params.descriptionClass);
            if (description) {
                description.classList.remove("d-none");
            } else {
                const descriptionEl = this.document.createElement("p");
                descriptionEl.classList.add(
                    params.descriptionClass,
                    "d-block",
                    "mt-2",
                    "pe-5",
                    "text-muted"
                );
                if (params.descriptionExtraClass) {
                    descriptionEl.classList.add(params.descriptionExtraClass);
                }
                descriptionEl.textContent = _t("Add a description here");
                item.appendChild(descriptionEl);
            }
        }
    }
    clean({ editingElement, params }) {
        const items = editingElement.querySelectorAll(`.${params.itemClass}`);
        for (const item of items) {
            const description = item.querySelector("." + params.descriptionClass);
            if (description) {
                description.classList.add("d-none");
            }
        }
    }
}

registry.category("website-plugins").add(PriceListPlugin.id, PriceListPlugin);
