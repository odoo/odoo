import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { BuilderAction } from "@html_builder/core/builder_action";
import { childNodeIndex } from "@html_editor/utils/position";

export class AddToCartOptionPlugin extends Plugin {
    static id = "addToCartOption";
    static dependencies = ["builderActions", "websiteBridge"];
    static shared = ["addToCartValues"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        so_content_addition_selectors: [".s_add_to_cart"],
        builder_actions: {
            ProductToCartAction,
            VariantToCartAction,
            AddToCartActionAction,
        },
        content_not_editable_selectors: ".s_add_to_cart:has(> button.s_add_to_cart_btn)",
        content_editable_selectors: ".s_add_to_cart > button.s_add_to_cart_btn",
    };
    addToCartValues() {
        return {
            addToCart: {
                action: "add_to_cart",
                icon: "add_shopping_cart",
                label: _t("Add to Cart"),
                content: this.dependencies.websiteBridge._t("Add to Cart"),
            },
            buyNow: {
                action: "buy_now",
                icon: "credit_card",
                label: _t("Buy Now"),
                content: this.dependencies.websiteBridge._t("Buy Now"),
            },
        };
    }
}

export class ProductToCartAction extends BuilderAction {
    static id = "productToCart";
    static dependencies = ["builderActions"];
    apply({ editingElement, value }) {
        const { id, type, product_variant_ids } = JSON.parse(value);

        editingElement.dataset.productTemplate = id;
        editingElement.dataset.productType = type;
        editingElement.dataset.variants = product_variant_ids.join(",");
        delete editingElement.dataset.productVariant;

        const buttonEl = editingElement.querySelector(".s_add_to_cart_btn");
        buttonEl.dataset.productTemplateId = id;
        buttonEl.dataset.productType = type;
        const oneVariant = product_variant_ids.length === 1;
        if (oneVariant) {
            buttonEl.dataset.productId = product_variant_ids[0];
        } else {
            delete buttonEl.dataset.productId;
        }
        buttonEl.removeAttribute("disabled");
        if (!oneVariant) {
            this.dependencies.builderActions
                .getAction("addToCartAction")
                .resetDefaultAction(editingElement);
        }
    }
    clean({ editingElement }) {
        delete editingElement.dataset.productTemplate;
        delete editingElement.dataset.productType;
        delete editingElement.dataset.variants;
        delete editingElement.dataset.productVariant;
        const buttonEl = editingElement.querySelector(".s_add_to_cart_btn");
        delete buttonEl.dataset.productTemplateId;
        delete buttonEl.dataset.productType;
        delete buttonEl.dataset.productId;
        buttonEl.setAttribute("disabled", "");
        this.dependencies.builderActions
            .getAction("addToCartAction")
            .resetDefaultAction(editingElement);
    }
    getValue({ editingElement }) {
        const value = {};
        const id = editingElement.dataset.productTemplate;
        if (!id) {
            return;
        }
        value.id = parseInt(id);
        const type = editingElement.dataset.productType;
        if (type !== undefined) {
            value.type = type;
        }
        const product_variant_ids = editingElement.dataset.variants
            ?.split(",")
            .map((el) => parseInt(el));
        if (product_variant_ids !== undefined) {
            value.product_variant_ids = product_variant_ids;
        }
        return JSON.stringify(value);
    }
}
export class VariantToCartAction extends BuilderAction {
    static id = "variantToCart";
    static dependencies = ["builderActions"];
    apply({ editingElement, value }) {
        const { id } = JSON.parse(value);
        editingElement.dataset.productVariant = id;
        const buttonEl = editingElement.querySelector(".s_add_to_cart_btn");
        buttonEl.dataset.productId = id;
    }
    clean({ editingElement }) {
        delete editingElement.dataset.productVariant;
        const buttonEl = editingElement.querySelector(".s_add_to_cart_btn");
        delete buttonEl.dataset.productId;
        this.dependencies.builderActions
            .getAction("addToCartAction")
            .resetDefaultAction(editingElement);
    }
    getValue({ editingElement }) {
        const id = editingElement.dataset.productVariant;
        if (id) {
            return JSON.stringify({ id: parseInt(id) });
        }
    }
}
export class AddToCartActionAction extends BuilderAction {
    static id = "addToCartAction";
    static dependencies = ["builderActions", "addToCartOption", "selection", "dom"];
    apply({ editingElement, params: { action, icon, content: label } }) {
        editingElement.dataset.action = action;
        const buttonEl = editingElement.querySelector(".s_add_to_cart_btn");
        buttonEl.dataset.action = action;
        const iconEl = buttonEl.querySelector("i");
        if (iconEl) {
            iconEl.dataset.icon = icon;
            this.dependencies.selection.setSelection({
                anchorNode: iconEl.parentElement,
                anchorOffset: childNodeIndex(iconEl) + 1,
                focusNode: buttonEl,
                focusOffset: buttonEl.childNodes.length,
            });
        } else {
            this.dependencies.selection.setSelection({
                anchorNode: buttonEl,
                anchorOffset: 0,
                focusNode: buttonEl,
                focusOffset: buttonEl.childNodes.length,
            });
        }
        this.dependencies.dom.insert(label);
    }
    isApplied({ editingElement, params: { action } }) {
        return editingElement.dataset.action === action;
    }

    resetDefaultAction(editingElement) {
        const addToCartValues = this.dependencies.addToCartOption.addToCartValues();
        if (this.isApplied({ editingElement, params: addToCartValues.buyNow })) {
            this.apply({ editingElement, params: addToCartValues.addToCart });
        }
    }
}

registry.category("website-plugins").add(AddToCartOptionPlugin.id, AddToCartOptionPlugin);
