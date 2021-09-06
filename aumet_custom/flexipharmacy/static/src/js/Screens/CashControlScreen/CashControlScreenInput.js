odoo.define('flexipharmacy.CashControlScreenInput', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class CashControlScreenInput extends PosComponent {
        constructor() {
            super(...arguments);
        }
        onKeyDown(e) {
            if(e.which == 13 || e.which == 9){
                this.props.line.line_total = this.props.line.coin_value * this.props.line.number_of_coins;
                this.trigger('main_total');
            }else if(e.which == 190){
               e.preventDefault();
            }
        }
        focusOut() {
            this.props.line.line_total = this.props.line.coin_value * this.props.line.number_of_coins;
            this.trigger('main_total');
        }
    }

    CashControlScreenInput.template = 'CashControlScreenInput';

    Registries.Component.add(CashControlScreenInput);

    return CashControlScreenInput;
});

