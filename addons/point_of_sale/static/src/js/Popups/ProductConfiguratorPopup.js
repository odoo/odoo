/** @odoo-module */
import { PosComponent } from "@point_of_sale/js/PosComponent";
import { AbstractAwaitablePopup } from "@point_of_sale/js/Popups/AbstractAwaitablePopup";

const { useState, useSubEnv } = owl;

export class BaseProductAttribute extends PosComponent {
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
        owl.onMounted(this.onMounted);
    }
    onMounted() {
        // With radio buttons `t-model` selects the default input by searching for inputs with
        // a matching `value` attribute. In our case, we use `t-att-value` so `value` is
        // not found yet and no radio is selected by default.
        // We then manually select the first input of each radio attribute.
        $(this.el).find('input[type="radio"]:first').prop("checked", true);
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
        ColorProductAttribute
    };

    setup() {
        super.setup();
        useSubEnv({ attribute_components: [] });
    }

    getPayload() {
        var selected_attributes = [];
        var price_extra = 0.0;

        this.env.attribute_components.forEach((attribute_component) => {
            const { value, extra } = attribute_component.getValue();
            selected_attributes.push(value);
            price_extra += extra;
        });

        return {
            selected_attributes,
            price_extra,
        };
    }
}
