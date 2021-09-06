odoo.define('flexipharmacy.TicketScreen', function(require) {
    'use strict';

    const TicketScreen = require('point_of_sale.TicketScreen')
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');


    const PosCustTicketScreen = TicketScreen =>
        class extends TicketScreen {
            selectOrder(order) {
                super.selectOrder(...arguments);
                if(this.env.pos.config.customer_display){
                    this.env.pos.get_order().mirror_image_data();
                }
            }
        };

    Registries.Component.extend(TicketScreen, PosCustTicketScreen);

    return TicketScreen;
});
