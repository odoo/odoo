
import { Plugin } from "@html_editor/plugin";
import { BuilderAction } from "@html_builder/core/builder_action";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class WishlistPageOption extends BaseOptionComponent {
    static template = "website_sale_wishlist.WishlistPageOption";
    static selector = ".o_wishlist_table"
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
            WishlistSetGapAction
        },
        save_handlers: this.onSave.bind(this),
    };

    async onSave() {
        const wishlistEl = this.editable.querySelector(".o_wishlist_table");
        if (!wishlistEl) return;

        const gridColumns = parseInt(wishlistEl.dataset.wishlistGridColumns) || 5;
        const mobileColumns = parseInt(wishlistEl.dataset.wishlistMobileColumns) || 2;
        const gap = wishlistEl.style.getPropertyValue("--o-wsale-wishlist-grid-gap") || "16px";

        return rpc("/shop/config/website", {
            wishlist_grid_columns: gridColumns,
            wishlist_mobile_columns: mobileColumns,
            wishlist_gap: gap,
        });
    }
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
