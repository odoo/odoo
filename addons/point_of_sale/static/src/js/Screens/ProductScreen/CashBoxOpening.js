odoo.define('point_of_sale.CashBoxOpening', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { Gui } = require('point_of_sale.Gui');

    class CashBoxOpening extends PosComponent {
        constructor() {
            super(...arguments);
            this.changes = {};
            this.defaultValue = this.env.pos.bank_statement.balance_start || 0;
            this.symbol = this.env.pos.currency.symbol;
        }
        captureChange(event) {
            this.changes[event.target.name] = event.target.value;
        }
        startSession() {
            let cashOpening = this.changes.cashBoxValue? this.changes.cashBoxValue: this.defaultValue;
            if(isNaN(cashOpening)) {
                Gui.showPopup('ErrorPopup',{
                    'title': 'Wrong value',
                    'body':  'Please insert a correct value.',
                });
                return;
            }
            this.env.pos.bank_statement.balance_start = cashOpening;
            this.env.pos.pos_session.state = 'opened';
            this.props.cashControl.cashControl = false;
            this.rpc({
                    model: 'pos.session',
                    method: 'set_cashbox_pos',
                    args: [this.env.pos.pos_session.id, cashOpening, this.changes.notes],
                });
        }
    }
    CashBoxOpening.template = 'CashBoxOpening';

    Registries.Component.add(CashBoxOpening);

    return CashBoxOpening;
});
