odoo.define('point_of_sale.ClientLine', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class ClientLine extends PosComponent {
        get highlight() {
            if (this.props.partner !== this.props.selectedClient) {
                return '';
            } else {
                return this.props.detailIsShown ? 'highlight' : 'lowlight';
            }
        }
    }
    ClientLine.template = 'ClientLine';

    Registries.Component.add(ClientLine);

    return ClientLine;
});
