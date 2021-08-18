odoo.define('point_of_sale.CustomerScreenButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { isRpcError } = require('point_of_sale.utils');
    var rpc = require('web.rpc');

    class CustomerScreenButton extends PosComponent {
        constructor() {
            super(...arguments);
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
        async onClick() {
            var self = this;
            await this.connectionCheck()
            if (this.get_connected){
                return self.env.pos.do_action({
                    type: 'ir.actions.act_url',
                    url: '/web/customer_display',
                });
            }else{
                this.get_connected = false;
            }
        }
    }
    CustomerScreenButton.template = 'CustomerScreenButton';

    Registries.Component.add(CustomerScreenButton);

    return CustomerScreenButton;
});
