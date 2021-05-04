/** @odoo-module alias=point_of_sale.ProductConfiguratorPopup **/

const { useState, useSubEnv } = owl.hooks;
import PosComponent from 'point_of_sale.PosComponent';

class ProductConfiguratorPopup extends owl.Component {
    constructor() {
        super(...arguments);
        useSubEnv({ attribute_components: [] });
    }
    confirm() {
        this.props.respondWith([true, this.getPayload()]);
    }
    cancel() {
        this.props.respondWith([false]);
    }
    getPayload() {
        var selected_attributes = [];
        var price_extra = 0.0;

        this.env.attribute_components.forEach((attribute_component) => {
            let { value, extra } = attribute_component.getValue();
            selected_attributes.push(value);
            price_extra += extra;
        });

        return {
            selected_attributes,
            price_extra,
        };
    }
}
ProductConfiguratorPopup.template = 'point_of_sale.ProductConfiguratorPopup';

class BaseProductAttribute extends PosComponent {
    constructor() {
        super(...arguments);

        this.env.attribute_components.push(this);

        this.attribute = this.props.attribute;
        this.values = this.attribute.values;
        this.state = useState({
            selected_value: parseFloat(this.values[0].id),
            custom_value: '',
        });
    }

    getValue() {
        let selected_value = this.values.find((val) => val.id === parseFloat(this.state.selected_value));
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

class RadioProductAttribute extends BaseProductAttribute {
    mounted() {
        // With radio buttons `t-model` selects the default input by searching for inputs with
        // a matching `value` attribute. In our case, we use `t-att-value` so `value` is
        // not found yet and no radio is selected by default.
        // We then manually select the first input of each radio attribute.
        $(this.el).find('input[type="radio"]:first').prop('checked', true);
    }
}
RadioProductAttribute.template = 'point_of_sale.RadioProductAttribute';

class SelectProductAttribute extends BaseProductAttribute {}
SelectProductAttribute.template = 'point_of_sale.SelectProductAttribute';

class ColorProductAttribute extends BaseProductAttribute {}
ColorProductAttribute.template = 'point_of_sale.ColorProductAttribute';

ProductConfiguratorPopup.components = { RadioProductAttribute, SelectProductAttribute, ColorProductAttribute };

export default {
    ProductConfiguratorPopup,
    BaseProductAttribute,
    RadioProductAttribute,
    SelectProductAttribute,
    ColorProductAttribute,
};
