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
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: ProductHeaderCategoryOption,
        builder_actions: {
            ToggleCategoryShowTitleAction,
            ToggleCategoryShowDescriptionAction,
            ToggleCategoryAlignContentAction,
        },
        dirt_marks: {
            id: "product-header",
            setDirtyOnMutation: (record) =>
                record.type === "classList" && record.target.id === "o_wsale_products_header"
                    ? record.target
                    : null,
            save: (el) =>
                rpc("/shop/config/category", {
                    category_id: el.dataset.categoryId,
                    show_category_title: el.classList.contains("o_wsale_products_header_show_category_title"),
                    show_category_description: el.classList.contains("o_wsale_products_header_show_category_description"),
                    align_category_content: el.classList.contains("o_wsale_products_header_category_center_content"),
                }),
        },
    };
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

registry
    .category("website-plugins")
    .add(ProductHeaderCategoryOptionPlugin.id, ProductHeaderCategoryOptionPlugin);
