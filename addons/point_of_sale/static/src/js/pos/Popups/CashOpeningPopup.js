/** @odoo-module alias=point_of_sale.CashOpeningPopup **/

const { useState } = owl.hooks;
import { parse } from 'web.field_utils';
import NumberBuffer from 'point_of_sale.NumberBuffer';

class CashOpeningPopup extends owl.Component {
    constructor() {
        super(...arguments);
        this.currency = this.env.model.currency;
        this.state = useState({
            notes: '',
            buffer: this.env.model.formatValue(this.env.model.backStatement.balance_start || 0),
        });
        NumberBuffer.use({
            nonKeyboardInputEvent: 'numpad-click-input',
            useWithBarcode: false,
            // Number buffer can take control on the state containing `buffer` property.
            state: this.state,
        });
    }
    async startSession() {
        this.env.model.backStatement.balance_start = parse.float(this.state.buffer);
        this.env.model.session.state = 'opened';
        await this.rpc({
            model: 'pos.session',
            method: 'set_cashbox_pos',
            args: [this.env.model.session.id, parse.float(this.state.buffer), this.state.notes],
        });
        this.props.respondWith(true);
    }
    sendInput(key) {
        this.trigger('numpad-click-input', { key });
    }
}

CashOpeningPopup.template = 'point_of_sale.CashOpeningPopup';

export default CashOpeningPopup;
