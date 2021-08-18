odoo.define('flexipharmacy.PaymentWalletPopup', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class PaymentWalletPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.state = useState({ inputchange: this.props.change});
            this.change = useRef('change');
        }
        async getPayload() {
            var order = this.env.pos.get_order();
            var cash_register_id = this.env.pos.pos_session.cash_register_id;
            if(!this.env.pos.config.cash_control){
                this.env.pos.db.notification('danger',this.env._t("Please enable cash control from point of sale settings."));
                return;
            }
            if(!cash_register_id){
                this.env.db.notification('danger',this.env._t("There is no cash register for this PoS Session."));
                return;
            }
            if(order.get_client()){
                order.set_type_for_wallet('change');
                order.set_change_amount_for_wallet(order.get_change());
            } else {
                if(confirm("To add money into wallet you have to select a customer or create a new customer \n Press OK for go to customer screen \n Press Cancel to Discard."))
                {
                    this._select_customer(order)
                }
            }
        }
        async _select_customer(order){
            const currentClient = order.get_client();
            const { confirmed, payload: newClient } = await this.showTempScreen(
                'ClientListScreen',
                { client: currentClient }
            );
            if (confirmed) {
                order.set_client(newClient);
                order.updatePricelist(newClient);
                this.showScreen('PaymentScreen');
            }
        }
        skip() {
            this.props.resolve({ skip: true });
            this.trigger('close-popup');
        }
        cancel() {
            this.trigger('close-popup');
        }
    }
    PaymentWalletPopup.template = 'PaymentWalletPopup';
    PaymentWalletPopup.defaultProps = {
        confirmText: 'Add to Wallet',
        skipText: 'Skip',
        cancelText: 'Cancel',
        title: '',
        body: '',
    };

    Registries.Component.add(PaymentWalletPopup);

    return PaymentWalletPopup;
});
