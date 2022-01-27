odoo.define('fg_custom.FgChannelButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');

    class FgChannelButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        async onClick() {
            const { confirmed, payload } = await this.showPopup('FgChannelPopup');
            var x_ext_source = '';
            if(payload!=null){
                 x_ext_source  = payload.x_ext_source;
            }
            if (confirmed) {
                const order = this.env.pos.get_order();
                order.x_ext_source = x_ext_source;
                order.trigger('change', order); // needed so that export_to_JSON gets triggered
                this.render();
                if(x_ext_source!=''){
                    document.getElementById('channelDiv').innerHTML  = x_ext_source;
                }else{
                    document.getElementById('channelDiv').innerHTML  = 'Select Channel';
                }

            }
        }
    }
    FgChannelButton.template = 'FgChannelButton';

    ProductScreen.addControlButton ({
       component: FgChannelButton,
       condition: function () {
           return true;
       }
   });

    Registries.Component.add(FgChannelButton);

    return FgChannelButton;
});
