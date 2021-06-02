/** @odoo-module alias=point_of_sale.NumberPopup **/

const { useState } = owl;
import NumberBuffer from 'point_of_sale.NumberBuffer';
import { useListener } from 'web.custom_hooks';
import Draggable from 'point_of_sale.Draggable';
import { _t } from 'web.core';

class NumberPopup extends owl.Component {
    /**
     * @param {Object} props
     * @param {Boolean} props.isPassword Show password popup.
     * @param {string | null} props.startingValue Starting value of the popup.
     * @param {Boolean} props.isInputSelected Input is highlighted and will reset upon a change.
     */
    constructor() {
        super(...arguments);
        useListener('accept-input', this.confirm);
        useListener('close-this-popup', this.cancel);
        this.state = useState({ buffer: this.props.startingValue || '', toStartOver: this.props.isInputSelected });
        NumberBuffer.use({
            nonKeyboardInputEvent: 'numpad-click-input',
            triggerAtEnter: 'accept-input',
            triggerAtEsc: 'close-this-popup',
            state: this.state,
        });
    }
    confirm() {
        if (NumberBuffer.get()) {
            this.props.respondWith([true, NumberBuffer.get()]);
        }
    }
    cancel() {
        this.props.respondWith([false]);
    }
    get decimalSeparator() {
        return this.env._t.database.parameters.decimal_point;
    }
    get inputBuffer() {
        if (this.state.buffer === null) {
            return '';
        }
        if (this.props.isPassword) {
            return this.state.buffer.replace(/./g, '•');
        } else {
            return this.state.buffer;
        }
    }
    sendInput(key) {
        this.trigger('numpad-click-input', { key });
    }
}
NumberPopup.components = { Draggable };
NumberPopup.template = 'point_of_sale.NumberPopup';
NumberPopup.defaultProps = {
    confirmText: _t('Ok'),
    cancelText: _t('Cancel'),
    title: _t('Confirm ?'),
    cheap: false,
    startingValue: null,
    isPassword: false,
};

export default NumberPopup;
