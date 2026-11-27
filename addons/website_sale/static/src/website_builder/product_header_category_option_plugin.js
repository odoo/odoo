import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";


export class ProductHeaderCategoryOptionPlugin extends Plugin {
    static id = "ProductHeaderCategoryOptionPlugin";

    resources = {
        builder_actions: {
            ToggleCategoryShowTitleAction,
            ToggleCategoryShowDescriptionAction,
            ToggleCategoryAlignContentAction,
        },

        // Send these settings only when the user toggled one of them. The header classes reflect
        // the settings as they were when the editor loaded, so sending them on every save would
        // overwrite changes made since then (e.g. by the AI).
        dirty_trackers: {
            selector: "#o_wsale_products_header",
            dirtyClass: "o_dirty_product_design_list",
            match: "self",
        },
        product_design_list_to_save: {
            selector: "#o_wsale_products_header",
            getData(el) {
                return {
                    show_category_title: el.classList.contains(
                        "o_wsale_products_header_show_category_title"
                    ),
                    show_category_description: el.classList.contains(
                        "o_wsale_products_header_show_category_description"
                    ),
                    align_category_content: el.classList.contains(
                        "o_wsale_products_header_category_center_content"
                    ),
                };
            },
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

registry.category("website-plugins").add(ProductHeaderCategoryOptionPlugin.id, ProductHeaderCategoryOptionPlugin);
