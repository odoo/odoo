
import { Plugin } from "@html_editor/plugin";
import { BuilderAction } from "@html_builder/core/builder_action";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class WishlistPageOption extends BaseOptionComponent {
    static template = "website_sale_wishlist.WishlistPageOption";
    static selector = "main:has(.o_wishlist_table)";
    static applyTo = ".o_wishlist_table";
    static editableOnly = false;
    static title = _t("Wishlist Page");
    static groups = ["website.group_website_designer"];
}

class WishlistPageOptionPlugin extends Plugin {
    static id = "wishlistPageOption";
    resources = {
        builder_options: WishlistPageOption,
        builder_actions: {
            WishlistGridColumnsAction,
            WishlistMobileColumnsAction,
            WishlistSetGapAction,
        },
        product_design_list_to_save: {
            selector: ".o_wishlist_table",
            getData(el) {
                const productOptClasses = Array.from(el.classList).filter((className) =>
                    className.startsWith("o_wsale_products_opt_")
                );
                return {
                    wishlist_grid_columns: parseInt(el.dataset.wishlistGridColumns) || 5,
                    wishlist_mobile_columns: parseInt(el.dataset.wishlistMobileColumns) || 2,
                    wishlist_gap:
                        el.style.getPropertyValue("--o-wsale-wishlist-grid-gap") || "16px",
                    wishlist_opt_products_design_classes: productOptClasses.join(" "),
                };
            },
        },
    };
}

export class WishlistGridColumnsAction extends BuilderAction {
    static id = "wishlistGridColumns";

    isApplied({ editingElement, value }) {
        return parseInt(editingElement.dataset.wishlistGridColumns) === value;
    }
    getValue({ editingElement }) {
        return parseInt(editingElement.dataset.wishlistGridColumns);
    }
    apply({ editingElement, value }) {
        editingElement.dataset.wishlistGridColumns = value;
    }
}

export class WishlistMobileColumnsAction extends BuilderAction {
    static id = "wishlistMobileColumns";

    isApplied({ editingElement, value }) {
        return parseInt(editingElement.dataset.wishlistMobileColumns) === value;
    }
    getValue({ editingElement }) {
        return parseInt(editingElement.dataset.wishlistMobileColumns);
    }
    apply({ editingElement, value }) {
        editingElement.dataset.wishlistMobileColumns = value;
    }
}

export class WishlistSetGapAction extends BuilderAction {
    static id = "wishlistSetGap";

    isApplied() {
        return true;
    }

    getValue({ editingElement }) {
        return editingElement.style.getPropertyValue("--o-wsale-wishlist-grid-gap");
    }

    apply({ editingElement, value }) {
        editingElement.style.setProperty("--o-wsale-wishlist-grid-gap", value);
    }
}

registry
    .category("website-plugins")
    .add(WishlistPageOptionPlugin.id, WishlistPageOptionPlugin);
