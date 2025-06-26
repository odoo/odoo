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

    apply(...args) {
        this._previewTemplate(true, ...args);
    }

    clean(...args) {
        this._previewTemplate(false, ...args);
    }

    _previewTemplate(apply, {
        editingElement,
        params: { templateId, previewClass, placeBefore, placeAfter, placeExcludeRootClosest, },
        selectableContext,
    }) {
        if (!apply && selectableContext) {
            return;
        }

        if (templateId && !editingElement.closest(placeExcludeRootClosest)) {
            const renderedEl = renderToElement(templateId);
            if (placeBefore) {
                for (const el of editingElement.querySelectorAll(placeBefore)) {
                    el.insertAdjacentElement('beforebegin', renderedEl.cloneNode(true));
                }
            }
            if (placeAfter) {
                for (const el of editingElement.querySelectorAll(placeAfter)) {
                    el.insertAdjacentElement('afterend', renderedEl.cloneNode(true));
                }
            }
        }

        if (previewClass) {
            editingElement.classList.add(...previewClass.split(" "));
        }
    }
}
class SetPpgAction extends BuilderAction {
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
class SetPprAction extends BuilderAction {
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
class SetGapAction extends BuilderAction {
    static id = "setGap";
    setup() {
        this.reload = {};
    }
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
class SetDefaultSortAction extends BuilderAction {
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
