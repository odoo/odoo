odoo.define('flexiretail_com_advance.CustomerScreen', function (require) {
    'use strict';
    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    const ClientListScreen = require('point_of_sale.ClientListScreen')
    var rpc = require('web.rpc');

    const CustomerScreen = (ClientListScreen) =>
        class extends ClientListScreen {
            constructor() {
                super(...arguments);
            }
            async onClick(){
                var self = this;
                var selected_id = this.state.selectedClient.id;
                var set_partner = this.env.pos.db.get_partner_by_id(selected_id);
                if(set_partner){
                    this.env.pos.get_order().set_client(set_partner);
                    var param_config = {
                        model: 'pos.config',
                        method: 'write',
                        args: [this.env.pos.config.id,{'default_customer_id':this.state.selectedClient.id}],
                    }
                    rpc.query(param_config, {async: false}).then(function(result){
                        if(result){
                            self.clickNext();
                        }
                    });
                }
            }
        };

    CustomerScreen.template = 'CustomerScreen';

    Registries.Component.extend(ClientListScreen, CustomerScreen);

    return CustomerScreen;
});
