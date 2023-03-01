/** @odoo-module */

import { Component, useState, useSubEnv, useRef } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
import { formatMonetary } from "@web/views/fields/formatters";
import { NavBar } from "@pos_self_order/NavBar/NavBar";
import { IncrementCounter } from "@pos_self_order/UtilComponents/IncrementCounter/IncrementCounter";
// ProductMainView.template = "ProductMainView";

export class ProductMainView extends Component {
    static template = "ProductMainView";
    setup() {
        this.state = useState(this.env.state);
        this.private_state = useState({
            qty: 1,
            customer_note: "",
            selectedVariants: Object.fromEntries(
                this.props.product.attributes.map((x) => [x.name, x.values[0].name])
            ),
        });

        // we look in the cart too see if the current product is already in it
        // if it is, we set the qty to the qty in the cart
        if (this.state.cart.some((item) => item.product_id === this.state.currentProduct)) {
            this.private_state.qty = this.state.cart.filter(
                (item) => item.product_id === this.state.currentProduct
            )[0].qty;
        }
        console.log("this.state :>> ", this.private_state);
        console.log("this.props.product.attributes :>> ", this.props.product.attributes);
        this.selfOrder = useSelfOrder();
        this.formatMonetary = formatMonetary;
    }
    findPriceExtraBasedOnSelectedValueOfCertainAttribute(attribute_name, value_name) {
        const attributesLegend = this.selfOrder.config.attributes_by_ptal_id;
        return attributesLegend[
            Object.keys(attributesLegend).filter((key) => attributesLegend[key].name === "Fabric")
        ].values.filter((value) => value.name === "Plastic")[0].price_extra;
    }
    findDescriptionOfProductBasedOnSelectedValuesOfAttributes(selectedVariants) {
        const attributesLegend = this.selfOrder.config.attributes_by_ptal_id;
        return Object.keys(attributesLegend)
            .map((key) => attributesLegend[key])
            .join(", ");
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
    static components = {
        NavBar,
        IncrementCounter,
    };
}

export default { ProductMainView };
