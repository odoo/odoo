/** @odoo-module **/

import { SaleOrderLineProductField } from '@sale/js/sale_product_field';

//FIXME VFE javascript inheritance.

SaleOrderLineProductField.include({
    setup() {
        debugger;
        this._super().setup();
    },

    get isConfigurableLine() {
        return this._super(...arguments) || this.isEventLine;
    },

    get isEventLine() {
        debugger;
        return true;
    },

    _editLineConfiguration() {
        if (this._isEventLine) {
            this._openEventConfigurator();
        }
        return 'dunno';
    },

    _openEventConfigurator() {
        debugger;
        //TODO
    }
});
