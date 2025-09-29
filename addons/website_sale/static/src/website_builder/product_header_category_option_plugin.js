import { Plugin } from "@html_editor/plugin";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";


export class ProductHeaderCategoryOptionPlugin extends Plugin {
    static id = "ProductHeaderCategoryOptionPlugin";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            ToggleCategoryShowTitleAction,
            ToggleCategoryShowDescriptionAction,
            ToggleCategoryAlignContentAction,
        },
        dirt_marks: {
            id: "product-header",
            setDirtyOnMutation: (mutation, targetNode) =>
                mutation.type === "classList" && targetNode.id === "o_wsale_products_header"
                    ? targetNode
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

export class BaseCategoryToggleAction extends BuilderAction {
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
