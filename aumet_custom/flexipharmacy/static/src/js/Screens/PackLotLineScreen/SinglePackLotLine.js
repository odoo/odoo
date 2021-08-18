odoo.define('point_of_sale.SinglePackLotLine', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class SinglePackLotLine extends PosComponent {
        constructor() {
            super(...arguments);
        }
        onKeyDown(e) {
            if(e.which == 96 || e.which == 110 || e.which == 190){
               e.preventDefault();
            }
        }
        onClickPlus(serial) {
            if(this.props.isSingleItem){
                if(this.props.serial.isSelected){
                    this.trigger('toggle-Lot');
                    this.props.serial.isSelected = !this.props.serial.isSelected;
                    this.trigger('toggle-button-highlight');
                    return;
                }
                if(!this.props.isLotSelected){
                    this.trigger('toggle-Lot');
                    this.props.serial.isSelected = !this.props.serial.isSelected;
                    this.trigger('toggle-button-highlight');
                }
                return;
            }
            this.props.serial.isSelected = !this.props.serial.isSelected;
            this.trigger('toggle-button-highlight');
            this.render();
        }
    }
    SinglePackLotLine.template = 'SinglePackLotLine';

    Registries.Component.add(SinglePackLotLine);

    return SinglePackLotLine;
});
