odoo.define('fg_custom.FgEmailReceiptButton', function (require) {
    'use strict';

    const { useListener } = require('web.custom_hooks');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { Printer } = require('point_of_sale.Printer');
    const { useRef } = owl.hooks;

    class FgEmailReceiptButton extends PosComponent {
        constructor() {
            super(...arguments);
            this.orderReceipt = useRef('order-receipt');
            this.props.inputEmail = this.props.inputEmail || (this.props.order.attributes.client && this.props.order.attributes.client.email) || '';

        }
        async emailReceipt() {
            var email = this.props.inputEmail || (this.props.order.attributes.client && this.props.order.attributes.client.email) || '';
            console.log(this.props);
            if(email){
               try {
                    await this._sendReceiptToCustomer(email);
//                    this.props.order.emailSuccessful = true;
//                    this.props.order.emailNotice = this.env._t('Email sent.');
//                    this.showPopup('', {
//                        title: this.env._t('Send Receipt'),
//                        body: this.env._t(
//                            'Email sent.'
//                        ),
//                    });
                    return;
                } catch (error) {
//                    this.props.order.emailSuccessful = false;
//                    this.props.order.emailNotice = this.env._t('Sending email failed. Please try again.');
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Send Receipt'),
                        body: this.env._t(
                            'Sending email failed. Please try again.'
                        ),
                    });
                    return;
                }
            }else{
                return;
            }
        }
        async _sendReceiptToCustomer(email) {

                const printer = new Printer(null, this.env.pos);
                const receiptString = this.orderReceipt.comp.el.outerHTML;
                const ticketImage = await printer.htmlToImg(receiptString);
                const order = this.props.order;
                const client = order.get_client();
                const orderName = order.get_name();
                const orderClient = { email: email, name: client ? client.name : email };
                const order_server_id = this.props.order.backendId;
                await this.rpc({
                    model: 'pos.order',
                    method: 'action_receipt_to_customer',
                    args: [[order_server_id], orderName, orderClient, ticketImage],
                });

            }
    }
    FgEmailReceiptButton.template = 'FgEmailReceiptButton';
    Registries.Component.add(FgEmailReceiptButton);

    return FgEmailReceiptButton;
});
//
//odoo.define('fg_custom.FgEmailReceiptButton', function (require) {
//    'use strict';
//
//    const AbstractReceiptScreen = require('point_of_sale.AbstractReceiptScreen');
//    const Registries = require('point_of_sale.Registries');
//    const PosComponent = require('point_of_sale.PosComponent');
//
//    const FgEmailReceiptButton = (AbstractReceiptScreen) => {
//        class FgEmailReceiptButton extends AbstractReceiptScreen {
//            constructor() {
//                super(...arguments);
//            }
//            mounted() {
//                this.emailReceipt();
//            }
//            async emailReceipt() {
//                console.log(this);
//                console.log(this.order);
//                console.log(this.orderUiState);
////                if (!is_email(this.orderUiState.inputEmail)) {
////                    this.orderUiState.emailSuccessful = false;
////                    this.orderUiState.emailNotice = this.env._t('Invalid email.');
////                    return;
////                }
////                try {
////                    await this._sendReceiptToCustomer();
////                    this.orderUiState.emailSuccessful = true;
////                    this.orderUiState.emailNotice = this.env._t('Email sent.');
////                } catch (error) {
////                    this.orderUiState.emailSuccessful = false;
////                    this.orderUiState.emailNotice = this.env._t('Sending email failed. Please try again.');
////                }
//            }
//        }
//        FgEmailReceiptButton.template = 'FgEmailReceiptButton';
//        return FgEmailReceiptButton;
//    };
//    Registries.Component.addByExtending(FgEmailReceiptButton, AbstractReceiptScreen);
//
//    return FgEmailReceiptButton;
//});

