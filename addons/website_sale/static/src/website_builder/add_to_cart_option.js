import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState, useGetItemValue } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";

export class AddToCartOption extends BaseOptionComponent {
    static id = "add_to_cart_option";
    static template = "website_sale.AddToCartOption";
    static dependencies = ["addToCartOption"];
    setup() {
        super.setup();
        this.getItemValue = useGetItemValue();
        this.domState = useDomState((editingElement) => ({
            shouldShowActionChoice:
                editingElement.dataset.variants?.split(",").length === 1 ||
                !!editingElement.dataset.productVariant,
        }));
        this.addToCartValues = this.dependencies.addToCartOption.addToCartValues();
    }

    getItemValueJSON(id) {
        const value = this.getItemValue(id);
        return value && JSON.parse(value);
    }
}

registry.category("website-options").add(AddToCartOption.id, AddToCartOption);
