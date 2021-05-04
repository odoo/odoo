/** @odoo-module alias=point_of_sale.NumpadWidget **/

import PosComponent from 'point_of_sale.PosComponent';

/**
 * @prop {'quantiy' | 'price' | 'discount'} activeMode
 * @emits set-numpad-mode @param {'quantiy' | 'price' | 'discount'} mode
 * @emits numpad-click-input @param {{ key: string }} key
 */
class NumpadWidget extends PosComponent {
    get hasPriceControlRights() {
        return this.env.model.config.restrict_price_control ? this.env.model.getIsCashierManager() : true;
    }
    get hasManualDiscount() {
        return this.env.model.config.manual_discount;
    }
    changeMode(mode) {
        if (!this.hasPriceControlRights && mode === 'price') {
            return;
        }
        if (!this.hasManualDiscount && mode === 'discount') {
            return;
        }
        this.trigger('set-numpad-mode', mode);
    }
    sendInput(key) {
        this.trigger('numpad-click-input', { key });
    }
    get decimalSeparator() {
        return this.env._t.database.parameters.decimal_point;
    }
}
NumpadWidget.template = 'point_of_sale.NumpadWidget';

export default NumpadWidget;
