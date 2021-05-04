/** @odoo-module alias=point_of_sale.NumberPopup **/

const { useState } = owl;
import NumberBuffer from 'point_of_sale.NumberBuffer';
import { useListener } from 'web.custom_hooks';
import Draggable from 'point_of_sale.Draggable';

class NumberPopup extends owl.Component {
    /**
     * @param {Object} props
     * @param {Boolean} props.isPassword Show password popup.
     * @param {number|null} props.startingValue Starting value of the popup.
     * @param {Boolean} props.isInputSelected Input is highlighted and will reset upon a change.
     *
     * Resolve to { confirmed, payload } when used with showPopup method.
     * @confirmed {Boolean}
     * @payload {String}
     */
    constructor() {
        super(...arguments);
        useListener('accept-input', this.confirm);
        useListener('close-this-popup', this.cancel);
        let startingBuffer = '';
        if (typeof this.props.startingValue === 'number' && this.props.startingValue > 0) {
            startingBuffer = this.props.startingValue.toFixed(2);
        }
        this.state = useState({ buffer: startingBuffer, toStartOver: this.props.isInputSelected });
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
    confirmText: 'Ok',
    cancelText: 'Cancel',
    title: 'Confirm ?',
    cheap: false,
    startingValue: null,
    isPassword: false,
};

export default NumberPopup;
