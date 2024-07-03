/** @odoo-module **/

import { jsonrpc } from "@web/core/network/rpc_service";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, onMounted } from "@odoo/owl";


export class PaymentHyperpayDialog extends Component {
    setup(){
        super.setup()
            var self = this;}

    static template = "hyperpay.payment_form_card";
    static components = { Dialog };
    static props = {
        order_id: String,
        ticket: String,
        moneris_redirect_uri:String,
        tokenizationRequested:String,
        env:Object,
    };
}
