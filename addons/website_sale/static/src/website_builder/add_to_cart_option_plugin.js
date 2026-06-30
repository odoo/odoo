import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { AddToCartOption, addToCartValues } from "./add_to_card_option";
import { BuilderAction } from "@html_builder/core/builder_action";

class AddToCartOptionPlugin extends Plugin {
    static id = "addToCartOption";
    static dependencies = ["builderActions"];
    resources = {
        builder_options: [AddToCartOption],
        so_content_addition_selector: [".s_add_to_cart"],
        builder_actions: {
            ProductToCartAction,
            VariantToCartAction,
            AddToCartActionAction,
        },
    };
}

export class ProductToCartAction extends BuilderAction {
    static id = "productToCart";
    static dependencies = ["builderActions"];
    apply({ editingElement, value }) {
        const classAction = this.dependencies.builderActions.getAction("classAction");

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
            buttonEl.dataset.productVariantId = product_variant_ids[0];
        } else {
            delete buttonEl.dataset.productVariantId;
        }
        classAction.clean({
            editingElement: buttonEl,
            params: { mainParam: "disabled" },
        });
        if (!oneVariant) {
            this.dependencies.builderActions
                .getAction("addToCartAction")
                .resetDefaultAction(editingElement);
        }
    }
    clean({ editingElement }) {
        const classAction = this.dependencies.builderActions.getAction("classAction");
        delete editingElement.dataset.productTemplate;
        delete editingElement.dataset.productType;
        delete editingElement.dataset.variants;
        delete editingElement.dataset.productVariant;
        const buttonEl = editingElement.querySelector(".s_add_to_cart_btn");
        delete buttonEl.dataset.productTemplateId;
        delete buttonEl.dataset.productType;
        delete buttonEl.dataset.productVariantId;
        classAction.apply({
            editingElement: buttonEl,
            params: { mainParam: "disabled" },
        });
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
        buttonEl.dataset.productVariantId = id;
    }
    clean({ editingElement }) {
        delete editingElement.dataset.productVariant;
        const buttonEl = editingElement.querySelector(".s_add_to_cart_btn");
        delete buttonEl.dataset.productVariantId;
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
    static dependencies = ["builderActions"];
    apply({ editingElement, params: { action, icon, label } }) {
        const classAction = this.dependencies.builderActions.getAction("classAction");
        editingElement.dataset.action = action;
        const buttonEl = editingElement.querySelector(".s_add_to_cart_btn");
        buttonEl.dataset.action = action;
        const iconEl = buttonEl.querySelector("i");
        classAction.apply({
            editingElement: iconEl,
            params: { mainParam: icon },
        });
        buttonEl.lastChild.textContent = label;
    }
    clean({ editingElement, params: { icon } }) {
        const classAction = this.dependencies.builderActions.getAction("classAction");

        delete editingElement.dataset.action;
        const buttonEl = editingElement.querySelector(".s_add_to_cart_btn");
        delete buttonEl.dataset.action;
        const iconEl = buttonEl.querySelector("i");
        classAction.clean({
            editingElement: iconEl,
            params: { mainParam: icon },
        });
    }
    isApplied({ editingElement, params: { action } }) {
        return editingElement.dataset.action === action;
    }

    resetDefaultAction(editingElement) {
        if (this.isApplied({ editingElement, params: addToCartValues.buyNow })) {
            this.clean({ editingElement, params: addToCartValues.buyNow });
            this.apply({ editingElement, params: addToCartValues.addToCart });
        }
    }
}

registry.category("website-plugins").add(AddToCartOptionPlugin.id, AddToCartOptionPlugin);
