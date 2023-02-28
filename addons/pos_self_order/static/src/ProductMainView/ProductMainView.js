/** @odoo-module */

const { Component, useState } = owl;
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
import { formatMonetary } from "@web/views/fields/formatters";
import { NavBar } from "../NavBar/NavBar.js";
import { IncrementCounter } from "../UtilComponents/IncrementCounter/IncrementCounter.js";
export class ProductMainView extends Component {
    setup() {
        this.state = useState(this.env.state);
        this.private_state = useState({
            qty: 1,
            customer_note: "",
        });
        if (this.state.cart.some((item) => item.product_id === this.state.currentProduct)) {
            this.private_state.qty = this.state.cart.filter(
                (item) => item.product_id === this.state.currentProduct
            )[0].qty;
        }
        this.selfOrder = useSelfOrder();
        this.formatMonetary = formatMonetary;
    }

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
        }
    };
    static components = { NavBar, IncrementCounter };
}
ProductMainView.template = "ProductMainView";

export default { ProductMainView };
