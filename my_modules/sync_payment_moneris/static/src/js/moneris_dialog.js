/** @odoo-module **/

import { jsonrpc } from "@web/core/network/rpc_service";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, onMounted } from "@odoo/owl";


export class PaymentMonerisDialog extends Component {
    setup(){
        super.setup()
        var self = this;
        onMounted(() => {

            // hide the close button for dialog from header
            $(".o_command_palette").find(".btn-close").hide()

            var myPageLoad = function (response) {
                console.log("myPageLoad response:", response)
            };

            var myCancelTransaction = function (response) {
                var myCheckout = new monerisCheckout();
                myCheckout.closeCheckout();
                jsonrpc(self.props.moneris_redirect_uri,{
                    response: response,
                    save_token: self.props.tokenizationRequested
                }).then(function (data) {
                    window.location.href = '/payment/status'
                });
            };

            var myPaymentReceipt =  function(response) {
                var myCheckout = new monerisCheckout();
                myCheckout.closeCheckout();
                jsonrpc(self.props.moneris_redirect_uri,{
                    response: response,
                    save_token: self.props.tokenizationRequested
                }).then(function (data) {
                    window.location.href = '/payment/status'
                });
            };

            var myPaymentComplete = function(response) {
                var myCheckout = new monerisCheckout();
                myCheckout.closeCheckout();
                jsonrpc(self.props.moneris_redirect_uri,{
                    response: response,
                    save_token: self.props.tokenizationRequested
                }).then(function (data) {
                    window.location.href = '/payment/status'
                });
            };

            var myErrorEvent = function(response) {
                var myCheckout = new monerisCheckout();
                myCheckout.closeCheckout();
                jsonrpc(self.props.moneris_redirect_uri,{
                    response: response,
                    save_token: self.props.tokenizationRequested
                }).then(function (data) {
                    window.location.href = '/payment/status'
                });
            };

            var myCheckout = new monerisCheckout();
            myCheckout.setMode(self.props.env);
            myCheckout.setCheckoutDiv("monerisCheckout");
            myCheckout.setCallback("page_loaded", myPageLoad);
            myCheckout.setCallback("cancel_transaction", myCancelTransaction);
            myCheckout.setCallback("error_event", myErrorEvent);
            myCheckout.setCallback("payment_receipt", myPaymentReceipt);
            myCheckout.setCallback("payment_complete", myPaymentComplete);
            myCheckout.startCheckout(self.props.ticket);
            $('#monerisCheckout').parent('div').addClass('moneris_checkout_content');
        });
    }
    static template = "payment_moneris.payment_form_card";
    static components = { Dialog };
    static props = {
        ticket: String,
        moneris_redirect_uri:String,
        tokenizationRequested:String,
        env:Object,
    };
}
