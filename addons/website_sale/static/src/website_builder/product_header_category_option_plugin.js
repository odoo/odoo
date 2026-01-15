import { Plugin } from "@html_editor/plugin";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";
import { _t } from "@web/core/l10n/translation";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class ProductHeaderCategoryOption extends BaseOptionComponent {
    static template = "website_sale.ProductHeaderCategoryOption";
    static selector = "#products_grid:has(header.o_wsale_products_header_is_category)";
    static editableOnly = false;
    static reloadTarget = true;
    static getSnippetTitle() {
        return _t((this.editable.querySelector("#o_wsale_products_header")?.dataset.categoryName || "Category") + ' Header');
    };
    static groups = ["website.group_website_restricted_editor"];
}

class ProductHeaderCategoryOptionPlugin extends Plugin {
    static id = "ProductHeaderCategoryOptionPlugin";

    resources = {
        builder_options: ProductHeaderCategoryOption,
        builder_actions: {
            ToggleCategoryShowTitleAction,
            ToggleCategoryShowDescriptionAction,
            ToggleCategoryAlignContentAction,
        },

        save_handlers: this.onSave.bind(this),
    };

    async onSave() {
        const headerEl = this.editable.querySelector("#o_wsale_products_header");
        if (!headerEl) return;
        const categoryId = headerEl.dataset.categoryId;

        const showTitle = headerEl.classList.contains("o_wsale_products_header_show_category_title");
        const showDescription = headerEl.classList.contains("o_wsale_products_header_show_category_description");
        const alignCategoryContent = headerEl.classList.contains("o_wsale_products_header_category_center_content");

        if (categoryId) {
            return rpc("/shop/config/category", {
                category_id: categoryId,
                show_category_title: showTitle,
                show_category_description: showDescription,
                align_category_content: alignCategoryContent,
            });
        }
    }
}

class BaseCategoryToggleAction extends BuilderAction {
    isApplied({ editingElement: el, params }) {
        return el.classList.contains(params.previewClass);
    }

    apply({ editingElement: el, params }) {
        el.classList.add(params.previewClass);
    }

    clean({ editingElement: el, params }) {
        el.classList.remove(params.previewClass);
    }
}

export class ToggleCategoryShowTitleAction extends BaseCategoryToggleAction {
    static id = "toggleCategoryShowTitle";
}

export class ToggleCategoryShowDescriptionAction extends BaseCategoryToggleAction {
    static id = "toggleCategoryShowDescription";
}

export class ToggleCategoryAlignContentAction extends BaseCategoryToggleAction {
    static id = "toggleCategoryAlignContent";
}

registry.category("website-plugins").add(ProductHeaderCategoryOptionPlugin.id, ProductHeaderCategoryOptionPlugin);
