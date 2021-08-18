odoo.define('flexipharmacy.NumpadWidget', function (require) {
    'use strict';

    const NumpadWidget = require('point_of_sale.NumpadWidget');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    
        const AsplRetNumpadWidgetInh = (NumpadWidget) =>
        class extends NumpadWidget {
            changeMode(mode) {
                if (!this.env.pos.get_order().get_refund_order()){
                    if (!this.hasPriceControlRights && mode === 'price') {
                        return;
                    }
                    if (!this.hasManualDiscount && mode === 'discount') {
                        return;
                    }
                    this.trigger('set-numpad-mode', { mode });
                }
            }
            sendInput(key) {
                if (!this.env.pos.get_order().get_refund_order()){
                    this.trigger('numpad-click-input', { key });
                }else{
                    if (key == "Backspace"){
                        this.trigger('numpad-click-input', { key });
                    }
                }
            }
        }

    Registries.Component.extend(NumpadWidget, AsplRetNumpadWidgetInh);

    return NumpadWidget;

});
