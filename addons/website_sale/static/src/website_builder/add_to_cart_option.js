import { BaseOptionComponent, useDomState, useGetItemValue } from "@html_builder/core/utils";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export const addToCartValues = {
    addToCart: { action: "add_to_cart", icon: "fa-cart-plus", label: _t("Add to Cart") },
    buyNow: { action: "buy_now", icon: "fa-credit-card", label: _t("Buy Now") },
};

export class AddToCartOption extends BaseOptionComponent {
    static id = "add_to_cart_option";
    static template = "website_sale.AddToCartOption";

    setup() {
        super.setup();
        this.getItemValue = useGetItemValue();
        this.domState = useDomState((editingElement) => ({
            shouldShowActionChoice:
                editingElement.dataset.variants?.split(",").length === 1 ||
                !!editingElement.dataset.productVariant,
        }));
        this.addToCartValues = addToCartValues;
    }

    getItemValueJSON(id) {
        const value = this.getItemValue(id);
        return value && JSON.parse(value);
    }
}

registry.category("builder-options").add(AddToCartOption.id, AddToCartOption);
