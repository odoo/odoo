odoo.define('point_of_sale.NumpadWidget', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');

    class NumpadWidget extends PosComponent {
        mounted() {
            this.props.state.on('change:mode', () => {
                this.render();
            });
            this.env.pos.on('change:cashier', () => {
                this.applyPriceControlRights();
            });
        }
        get hasPriceControlRights() {
            const cashier = this.env.pos.get('cashier') || this.env.pos.get_cashier();
            return !this.env.pos.config.restrict_price_control || cashier.role == 'manager';
        }
        applyPriceControlRights() {
            if (this.hasPriceControlRights && this.props.state.get('mode') == 'price') {
                this.props.state.changeMode('quantity');
            }
            this.render();
        }
        clickDeleteLastChar() {
            return this.props.state.deleteLastChar();
        }
        clickSwitchSign() {
            return this.props.state.switchSign();
        }
        clickAppendNewChar(event) {
            const newChar = event.target.innerText || event.target.textContent;
            return this.props.state.appendNewChar(newChar);
        }
        clickChangeMode(event) {
            const newMode = event.target.attributes['data-mode'].nodeValue;
            return this.props.state.changeMode(newMode);
        }
    }

    return { NumpadWidget };
});
