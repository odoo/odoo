odoo.define('point_of_sale.ReferenceClientLine', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class ReferenceClientLine extends PosComponent {
        get highlight() {
            if(this.props.flag == "show_doctor"){
                return this.props.partner !== this.props.selectedDoctor ? '' : 'highlight';
            }else{
                 return this.props.partner !== this.props.selectedRefClient ? '' : 'highlight';
            }
        }
    }
    ReferenceClientLine.template = 'ReferenceClientLine';

    Registries.Component.add(ReferenceClientLine);

    return ReferenceClientLine;
});
