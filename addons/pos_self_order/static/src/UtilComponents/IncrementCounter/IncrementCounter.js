/** @odoo-module */

const { Component } = owl;
import { useSelfOrder } from "@pos_self_order/SelfOrderService";

// this is a counter component that can be used to increment or decrement a number
// it is used in the main product view to increment or decrement the quantity of a product
// you need to pass the following props to this component:
// function to call when the counter is incremented or decremented;
// this function will change the state of the parent component
export class IncrementCounter extends Component {
    setup() {
        this.selfOrder = useSelfOrder();
    }
}
IncrementCounter.template = "IncrementCounter";
export default { IncrementCounter };
