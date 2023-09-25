/** @odoo-module */
import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { Component, useRef, useState, useSubEnv } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class BaseProductAttribute extends Component {
    setup() {
        this.env.attribute_components.push(this);
        this.attribute = this.props.attribute;
        this.values = this.attribute.values;
        this.state = useState({
            attribute_value_ids: parseFloat(this.values[0].id),
            custom_value: "",
        });
    }

    getValue() {
        const attribute_value_ids =
            this.attribute.display_type === "multi"
                ? this.values.filter((val) => this.state.attribute_value_ids[val.id])
                : [this.values.find((val) => val.id === parseInt(this.state.attribute_value_ids))];

        const extra = attribute_value_ids.reduce((acc, val) => acc + val.price_extra, 0);
        const valueIds = attribute_value_ids.map((val) => val.id);
        const value = attribute_value_ids
            .map((val) => {
                if (val.is_custom && this.state.custom_value) {
                    return `${val.name}: ${this.state.custom_value}`;
                }
                return val.name;
            })
            .join(", ");

        return {
            value,
            valueIds,
            extra,
        };
    }
}

export class RadioProductAttribute extends BaseProductAttribute {
    static template = "point_of_sale.RadioProductAttribute";

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
    static template = "point_of_sale.SelectProductAttribute";
}

export class ColorProductAttribute extends BaseProductAttribute {
    static template = "point_of_sale.ColorProductAttribute";
}

export class MultiProductAttribute extends BaseProductAttribute {
    static template = "point_of_sale.MultiProductAttribute";

    setup() {
        super.setup();
        this.state = useState({
            attribute_value_ids: [],
            custom_value: "",
        });

        this.initAttribute();
    }

    initAttribute() {
        const attribute = this.props.attribute;

        for (const value of attribute.values) {
            this.state.attribute_value_ids[value.id] = false;
        }
    }
}

export class ProductConfiguratorPopup extends AbstractAwaitablePopup {
    static template = "point_of_sale.ProductConfiguratorPopup";
    static components = {
        RadioProductAttribute,
        SelectProductAttribute,
        ColorProductAttribute,
        MultiProductAttribute,
    };

    setup() {
        super.setup();
        useSubEnv({ attribute_components: [] });
        this.state = useState({
            quantity: this.props.quantity || 1,
        });
        this.ui = useService("ui");
    }

    getPayload() {
        const selected_attributes = [];
        let attribute_value_ids = [];
        var price_extra = 0.0;
        const quantity = this.state.quantity;

        this.env.attribute_components.forEach((attribute_component) => {
            const { value, valueIds, extra } = attribute_component.getValue();
            selected_attributes.push(value);
            attribute_value_ids.push(valueIds);
            price_extra += extra;
        });

        attribute_value_ids = attribute_value_ids.flat();
        return {
            selected_attributes,
            attribute_value_ids,
            price_extra,
            quantity,
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
