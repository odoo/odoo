/** @odoo-module */
import { AbstractAwaitablePopup } from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import { Component, useRef, useState, useSubEnv } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class BaseProductAttribute extends Component {
    setup() {
        super.setup();
        this.env.attribute_components.push(this);
        this.attribute = this.props.attribute;
        this.values = this.attribute.values;
        this.state = useState({
            selected_value: parseFloat(this.values[0].id),
            custom_value: "",
        });
    }

    getValue() {
        const selected_value = this.values.find(
            (val) => val.id === parseFloat(this.state.selected_value)
        );
        let value = selected_value.name;
        if (selected_value.is_custom && this.state.custom_value) {
            value += `: ${this.state.custom_value}`;
        }

        return {
            value,
            extra: selected_value.price_extra,
        };
    }
}

export class RadioProductAttribute extends BaseProductAttribute {
    static template = "RadioProductAttribute";

    setup() {
        super.setup();
        this.root = useRef("root");
        owl.onMounted(this.onMounted);
    }
    onMounted() {
        // With radio buttons `t-model` selects the default input by searching for inputs with
        // a matching `value` attribute. In our case, we use `t-att-value` so `value` is
        // not found yet and no radio is selected by default.
        // We then manually select the first input of each radio attribute.
        this.root.el.querySelector("input[type=radio]").checked = true;
    }
}

export class SelectProductAttribute extends BaseProductAttribute {
    static template = "SelectProductAttribute";
}

export class ColorProductAttribute extends BaseProductAttribute {
    static template = "ColorProductAttribute";
}

export class ProductConfiguratorPopup extends AbstractAwaitablePopup {
    static template = "ProductConfiguratorPopup";
    static components = {
        RadioProductAttribute,
        SelectProductAttribute,
        ColorProductAttribute,
    };

    setup() {
        super.setup();
        useSubEnv({ attribute_components: [] });
        this.state = useState({
            quantity: 1,
        });
        this.ui = useService("ui");
    }

    getPayload() {
        var selected_attributes = [];
        var price_extra = 0.0;
        const quantity = this.state.quantity;

        this.env.attribute_components.forEach((attribute_component) => {
            const { value, extra } = attribute_component.getValue();
            selected_attributes.push(value);
            price_extra += extra;
        });

        if (quantity > 1) {
            return {
                selected_attributes,
                price_extra,
                quantity,
            };
        }

        return {
            selected_attributes,
            price_extra,
        };
    }
    get imageUrl() {
        const product = this.props.product;
        return `/web/image?model=product.product&field=image_128&id=${product.id}&unique=${product.write_date}`;
    }
    get unitPrice() {
        return this.env.utils.formatCurrency(this.props.product.lst_price);
    }
    addOneQuantity() {
        ++this.state.quantity;
    }
    removeOneQuantity() {
        if (this.state.quantity == 1) {
            return;
        }
        --this.state.quantity;
    }
}
