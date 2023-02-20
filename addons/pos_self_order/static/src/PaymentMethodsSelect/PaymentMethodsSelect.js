/** @odoo-module */

const { Component, useState } = owl;
import { _t } from "@web/core/l10n/translation";
import { NavBar } from "../NavBar/NavBar";

export class PaymentMethodsSelect extends Component {
    setup() {
        this.state = useState(this.env.state); 
    }
    makePayment = (payment_option) => {
        if(payment_option.name == 'Online Payment') {
            const payment_link = `/pos-self-order/pay?pos_order_id=${this.state.order_to_pay.order_id}&access_token=${this.state.order_to_pay.access_token}`;
            window.location = payment_link;
            return
        }
        // TODO: send an http request to the server to register the intention to pay with this payment option
        // TODO: create the route to handle this request on the backend
        // TODO: somehow show this --intent to pay-- to the waiter in the regular POS
        this.state.message_to_display = `Your intention to pay with ${payment_option.name} has been registered. Please wait for the waiter.`;
        this.props.goBack();
    }
    static components = { NavBar };  
}
PaymentMethodsSelect.template = 'PaymentMethodsSelect'
export default { PaymentMethodsSelect };

