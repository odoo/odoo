odoo.define('flexipharmacy.PurchaseHistoryPopup', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const { useListener } = require('web.custom_hooks');
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class PurchaseHistoryPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.state = useState({ ProductPurchaseHistory: 'CartProductPurchaseHistory'});
            useListener('print-product-and-order-receipt', this.PrintProductAndOrderReceipt);
        }
        CartProductPurchaseHistory(){
            this.state.ProductPurchaseHistory = 'CartProductPurchaseHistory';
        }
        LastOrderHistory(){
            this.state.ProductPurchaseHistory = 'LastOrderHistory';
        }
        async PrintProductAndOrderReceipt(){
            var use_posbox = this.env.pos.config.is_posbox && (this.env.pos.config.iface_print_via_proxy);
            if (use_posbox || this.env.pos.config.other_devices) {
                const report = this.env.qweb.renderToString( 'PurchaseHistoryReceipt',{
                    props: {'ProductPurchaseHistory':this.state.ProductPurchaseHistory, 'product_history': this.props.product_history, 'last_purchase_history': this.props.last_purchase_history, 'customer_name': this.env.pos.get_order().get_client_name(), 'last-order-name': this.props.last_order_name, 'last_order_date': this.props.last_order_date, 'pos': this.env.pos},

                });
                const printResult = await this.env.pos.proxy.printer.print_receipt(report);
                if (!printResult.successful) {
                    await this.showPopup('ErrorPopup', {
                        title: printResult.message.title,
                        body: printResult.message.body,
                    });
                }
                this.trigger('close-popup');
            } else {
                this.showScreen('ReceiptScreen', {'check':'from_product_history', 'ProductPurchaseHistory':this.state.ProductPurchaseHistory, 'product_history': this.props.product_history, 'last_purchase_history': this.props.last_purchase_history, 'customer_name': this.env.pos.get_order().get_client_name(), 'last_order_name': this.props.last_order_name, 'last_order_date': this.props.last_order_date,'pos': this.env.pos});
                this.trigger('close-popup');
            }
        }
        cancel() {
            this.trigger('close-popup');
        }
    }
    PurchaseHistoryPopup.template = 'PurchaseHistoryPopup';
    PurchaseHistoryPopup.defaultProps = {
        confirmText: 'Add to Wallet',
        cancelText: 'Cancel',
        title: '',
        body: '',
    };

    Registries.Component.add(PurchaseHistoryPopup);

    return PurchaseHistoryPopup;
});
