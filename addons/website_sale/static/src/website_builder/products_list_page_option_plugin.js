import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";
import { ProductsListPageOption } from "@website_sale/website_builder/products_list_page_option";

class ProductsListPageOptionPlugin extends Plugin {
    static id = "productsListPageOptionPlugin";

    resources = {
        builder_options: [
            {
                OptionComponent: ProductsListPageOption,
                selector: "main:has(.o_wsale_products_page)",
                applyTo: "#o_wsale_container",
                editableOnly: false,
                title: _t("Products Page"),
                groups: ["website.group_website_designer"],
            },
        ],
        builder_actions: {
            PreviewTemplateAction,
            SetPpgAction,
            SetPprAction,
            SetGapAction,
            SetDefaultSortAction,
        },
        save_handlers: this.onSave.bind(this),
    };

    async onSave() {
        const pageEl = this.editable.querySelector("#o_wsale_container");
        if (pageEl) {
            const gapToSave = pageEl.dataset.gapToSave;
            if (typeof gapToSave !== "undefined") {
                return rpc("/shop/config/website", { shop_gap: gapToSave });
            }
        }
    }
}

class PreviewTemplateAction extends BuilderAction {
    static id = "previewTemplate";
    static dependencies = ["savePlugin"];

    getPreviewTemplateIsPresentClass(templateId) {
        return `preview_is_present_${templateId?.replace(/\./g, "_")}`;
    }

    async apply({
        editingElement: el,
        isPreviewing,
        params: {
            templateId,
            previewClass,
            placeBefore,
            placeAfter,
            placeFirstChild,
            placeLastChild,
            placeExcludeRootClosest,
        },
    }) {
        const previewIsPresentClass = this.getPreviewTemplateIsPresentClass(templateId);
        if (templateId && !el.classList.contains(previewIsPresentClass)) {
            const renderedEl = renderToElement(templateId);
            let targetEl = el;
            if (placeExcludeRootClosest) {
                targetEl = el.closest(placeExcludeRootClosest);
            }
            let elementInserted = false;
            if (targetEl) {
                if (placeBefore) {
                    for (const el of targetEl.querySelectorAll(placeBefore)) {
                        el.insertAdjacentElement("beforebegin", renderedEl.cloneNode(true));
                        elementInserted = true;
                    }
                }
                if (placeAfter) {
                    for (const el of targetEl.querySelectorAll(placeAfter)) {
                        el.insertAdjacentElement("afterend", renderedEl.cloneNode(true));
                        elementInserted = true;
                    }
                }
                if (placeFirstChild) {
                    for (const el of targetEl.querySelectorAll(placeFirstChild)) {
                        el.insertAdjacentElement("afterbegin", renderedEl.cloneNode(true));
                        elementInserted = true;
                    }
                }
                if (placeLastChild) {
                    for (const el of targetEl.querySelectorAll(placeLastChild)) {
                        el.insertAdjacentElement("beforeend", renderedEl.cloneNode(true));
                        elementInserted = true;
                    }
                }
            }
            if (!isPreviewing && !elementInserted) {
                // If we can't preview the action (e.g. `targetEl` not found)
                // we need to reload the editor to show the changes. Note that
                // the first part of the composite action,
                // `previewableWebsiteConfig`, has already registered which
                // views to enable/disable on save.
                await this.dependencies.savePlugin.save();
                await this.config.reloadEditor();
            }
            el.classList.add(previewIsPresentClass);
        }
        if (previewClass) {
            previewClass.split(/\s+/).forEach((cls) => el.classList.add(cls));
        }
    }

    async clean({ editingElement: el, isPreviewing, params: { templateId, previewClass } }) {
        const previewIsPresentClass = this.getPreviewTemplateIsPresentClass(templateId);
        if (previewClass) {
            previewClass.split(/\s+/).forEach((cls) => el.classList.remove(cls));
        }
        if (!isPreviewing && !el.classList.contains(previewIsPresentClass)) {
            // If the preview template is not present, we can't preview the
            // action by hiding the template. We need to reload the editor to
            // show the changes. Note that the first part of the composite
            // action, `previewableWebsiteConfig`, has already registered which
            // views to enable/disable on save.
            await this.dependencies.savePlugin.save();
            await this.config.reloadEditor();
        }
    }
}

export class SetPpgAction extends BuilderAction {
    static id = "setPpg";
    setup() {
        this.reload = {};
    }
    getValue({ editingElement }) {
        return parseInt(editingElement.dataset.ppg);
    }
    apply({ value }) {
        const PPG_LIMIT = 10000;
        let ppg = parseInt(value);
        if (!ppg || ppg < 1) {
            return false;
        }
        ppg = Math.min(ppg, PPG_LIMIT);
        return rpc("/shop/config/website", { shop_ppg: ppg });
    }
}
export class SetPprAction extends BuilderAction {
    static id = "setPpr";
    setup() {
        this.reload = {};
    }
    isApplied({ editingElement, value }) {
        return parseInt(editingElement.dataset.ppr) === value;
    }
    apply({ value }) {
        const ppr = parseInt(value);
        return rpc("/shop/config/website", { shop_ppr: ppr });
    }
}
export class SetGapAction extends BuilderAction {
    static id = "setGap";
    isApplied() {
        return true;
    }
    getValue({ editingElement }) {
        return editingElement.style.getPropertyValue("--o-wsale-products-grid-gap");
    }
    apply({ editingElement, value }) {
        editingElement.style.setProperty("--o-wsale-products-grid-gap", value);
        editingElement.dataset.gapToSave = value;
    }
}

export class SetDefaultSortAction extends BuilderAction {
    static id = "setDefaultSort";
    setup() {
        this.reload = {};
    }
    isApplied({ editingElement, value }) {
        return editingElement.dataset.defaultSort === value;
    }
    apply({ value }) {
        return rpc("/shop/config/website", { shop_default_sort: value });
    }
}

registry
    .category("website-plugins")
    .add(ProductsListPageOptionPlugin.id, ProductsListPageOptionPlugin);
