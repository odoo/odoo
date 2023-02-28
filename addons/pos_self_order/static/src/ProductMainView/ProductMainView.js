/** @odoo-module */

import { Component, useState, useSubEnv, useRef } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
import { formatMonetary } from "@web/views/fields/formatters";
import { NavBar } from "@pos_self_order/NavBar/NavBar";
import { IncrementCounter } from "@pos_self_order/UtilComponents/IncrementCounter/IncrementCounter";
// ProductMainView.template = "ProductMainView";

export class BaseProductAttribute extends Component {
    setup() {
        this.private_state = useState(this.env.private_state);
        // FIXME: i think the problem is here.
        this.private_state.attribute_components.push(this);
        this.attribute = this.private_state.attributes;
        console.log("objecsalutaraet");
        console.log("this.attribute :>> ", this.attribute);
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
        this.root = useRef("root");
        owl.onMounted(this.onMounted);
    }
    onMounted() {
        // With radio buttons `t-model` selects the default input by searching for inputs with
        // a matching `value` attribute. In our case, we use `t-att-value` so `value` is
        // not found yet and no radio is selected by default.
        // We then manually select the first input of each radio attribute.
        // this.root.el.querySelector("input[type=radio]").checked = true;
    }
}
export class SelectProductAttribute extends BaseProductAttribute {
    static template = "SelectProductAttribute";
}

export class ColorProductAttribute extends BaseProductAttribute {
    static template = "ColorProductAttribute";
}

export class ProductMainView extends Component {
    static template = "ProductMainView";
    setup() {
        this.state = useState(this.env.state);
        this.private_state = useState({
            qty: 1,
            customer_note: "",
            // selectedVariants: this.props.product.attributes.map((attr) => {
            //     attr[0].name;
            // }),
            attribute_components: [],
            attributes: this.props.product.attributes,
        });
        useSubEnv({ private_state: this.private_state });

        if (this.state.cart.some((item) => item.product_id === this.state.currentProduct)) {
            this.private_state.qty = this.state.cart.filter(
                (item) => item.product_id === this.state.currentProduct
            )[0].qty;
        }
        this.selfOrder = useSelfOrder();
        this.formatMonetary = formatMonetary;
    }
    // FIXME
    onMounted() {
        // With radio buttons `t-model` selects the default input by searching for inputs with
        // a matching `value` attribute. In our case, we use `t-att-value` so `value` is
        // not found yet and no radio is selected by default.
        // We then manually select the first input of each radio attribute.
        $(this.el).find('input[type="radio"]:first').prop("checked", true);
    }
    setValue = (qty) => {
        if (qty >= 0) {
            this.private_state.qty = qty;
            console.log(
                "this.private_state.selectedVariants :>> ",
                this.props.product.attributes.map((x) => x.name)
            );
        }
    };
    getPayload() {
        var selected_attributes = [];
        var price_extra = 0.0;

        this.private_state.attribute_components.forEach((attribute_component) => {
            const { value, extra } = attribute_component.getValue();
            selected_attributes.push(value);
            price_extra += extra;
        });

        return {
            selected_attributes,
            price_extra,
        };
    }
    static components = {
        NavBar,
        IncrementCounter,
        BaseProductAttribute,
        RadioProductAttribute,
        SelectProductAttribute,
        ColorProductAttribute,
    };
}
export default { ProductMainView };
