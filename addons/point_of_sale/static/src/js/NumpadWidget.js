odoo.define('point_of_sale.NumpadWidget', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');

    class NumpadWidget extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = this.props.state;
            this.pos = this.props.pos;
        }
        mounted() {
            this.state.on('change:mode', () => {
                this.render();
            });
            this.pos.on('change:cashier', () => {
                this.applyPriceControlRights();
            });
        }
        get hasPriceControlRights() {
            const cashier = this.pos.get('cashier') || this.pos.get_cashier();
            return !this.pos.config.restrict_price_control || cashier.role == 'manager';
        }
        applyPriceControlRights() {
            if (this.hasPriceControlRights && this.state.get('mode') == 'price') {
                this.state.changeMode('quantity');
            }
            this.render();
        }
        clickDeleteLastChar() {
            return this.state.deleteLastChar();
        }
        clickSwitchSign() {
            return this.state.switchSign();
        }
        clickAppendNewChar(event) {
            const newChar = event.target.innerText || event.target.textContent;
            return this.state.appendNewChar(newChar);
        }
        clickChangeMode(event) {
            const newMode = event.target.attributes['data-mode'].nodeValue;
            return this.state.changeMode(newMode);
        }
    }

    return { NumpadWidget };
});
