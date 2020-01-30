odoo.define('point_of_sale.ActionpadWidget', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');

    // const { ConfirmDialog } = require('point_of_sale.ConfirmDialog');

    class ActionpadWidget extends PosComponent {
        constructor() {
            super(...arguments);
            this.pos = this.props.pos;
            this.gui = this.props.gui;
        }
        mounted() {
            this.pos.on('change:selectedClient', () => {
                this.render();
            });
        }
        willUnmount() {
            this.pos.off('change:selectedClient');
        }
        get isLongName() {
            return this.pos.get_client() && this.pos.get_client().name.length > 10;
        }
        get client() {
            return this.pos.get_client();
        }
        startPayment() {
            // const productLotsAreValid = this.pos
            //     .get_order()
            //     .get_orderlines()
            //     .every(line => line.has_valid_product_lot());

            // if (!productLotsAreValid) {
            //     try{
            //         let userResponse = ConfirmDialog.show({
            //             title: _t('Empty Serial/Lot Number'),
            //             body: _t('One or more product(s) required serial/lot number.'),
            //         })
            //         if (userResponse) {
            //             this.trigger('start-payment');
            //         }
            //     } catch (err) {
            //         // log error or show another popup?
            //     }
            // } else {
            //     this.trigger('start-payment');
            // }

            // temporary: immediately show the payment screen
            // The real implementation should be checking the product lots
            // validity first. The above commented code is the proposed
            // implementation.
            this.trigger('show-screen', { screenName: 'PaymentScreen' });
        }
        selectCustomer() {
            this.trigger('show-screen', { screenName: 'ClientListScreen' });
        }
    }

    return { ActionpadWidget };
});
