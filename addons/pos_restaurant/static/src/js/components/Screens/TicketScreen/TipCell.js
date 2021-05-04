odoo.define('pos_restaurant.TipCell', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const { useAutofocus } = require('web.custom_hooks');
    const { parse } = require('web.field_utils');
    const { useState } = owl.hooks;

    class TipCell extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({ isEditing: false, ...this.props.order._extras.TipScreen });
            useAutofocus({ selector: 'input' });
        }
        patched() {
            this.props.order._extras.TipScreen.inputTipAmount = this.state.inputTipAmount;
        }
        get tipAmountStr() {
            return this.env.model.formatCurrency(parse.float(this.state.inputTipAmount || '0'));
        }
        onBlur() {
            this.state.isEditing = false;
        }
        onKeydown(event) {
            if (event.key === 'Enter') {
                this.state.isEditing = false;
            }
        }
        editTip() {
            this.state.isEditing = true;
        }
    }
    TipCell.template = 'pos_restaurant.TipCell';

    return TipCell;
});
