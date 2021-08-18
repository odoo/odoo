odoo.define('flexipharmacy.OpenDetailButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useState } = owl.hooks;
    const { useListener } = require('web.custom_hooks');
    const { isRpcError } = require('point_of_sale.utils');
    var rpc = require('web.rpc');
    const Registries = require('point_of_sale.Registries');

    class OpenDetailButton extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({ flag: false, componentFlag: false});
            useListener('close-side-menu', () => this.toggle('flag'));
            this.get_connected = true
        }
        async connectionCheck(){
            var self = this;
            try {
                await rpc.query({
                    model: 'pos.session',
                    method: 'connection_check',
                    args: [this.env.pos.pos_session.id],
                });
                this.get_connected = true
                this.env.pos.get_order().set_connected(true)
            } catch (error) {
                if (isRpcError(error) && error.message.code < 0) {
                    this.get_connected = false
                    this.env.pos.get_order().set_connected(false)
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Network Error'),
                        body: this.env._t('Cannot access order management screen if offline.'),
                    });
                } else {
                    throw error;
                }
            }            
        }
        async toggle(key) {
            await this.connectionCheck()
            if (this.get_connected){
                this.trigger('close-side-sub-menu')
                this.state[key] = !this.state[key];
            }else{
                this.get_connected = false;
            }
        }
    }
    OpenDetailButton.template = 'OpenDetailButton';

    Registries.Component.add(OpenDetailButton);

    return OpenDetailButton;
});
