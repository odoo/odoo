import { Plugin } from "@html_editor/plugin";
import { BuilderAction } from "@html_builder/core/builder_action";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export class WishlistPageOptionPlugin extends Plugin {
    static id = "wishlistPageOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            WishlistGridColumnsAction,
            WishlistMobileColumnsAction,
            WishlistSetGapAction,
        },
        dirt_marks: {
            id: "wishlist-table",
            setDirtyOnMutation: (mutation, targetNode) =>
                mutation.type === "attributes" && targetNode.matches?.(".o_wishlist_table")
                    ? targetNode
                    : null,
            save: (el) =>
                rpc("/shop/config/website", {
                    wishlist_grid_columns: parseInt(el.dataset.wishlistGridColumns) || 5,
                    wishlist_mobile_columns: parseInt(el.dataset.wishlistMobileColumns) || 2,
                    wishlist_gap:
                        el.style.getPropertyValue("--o-wsale-wishlist-grid-gap") || "16px",
                }),
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

registry.category("website-plugins").add(WishlistPageOptionPlugin.id, WishlistPageOptionPlugin);
