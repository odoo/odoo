odoo.define('point_of_sale.ClientLine', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class ClientLine extends PosComponent {
        get highlight() {
            return this.props.selectedClient && this.props.selectedClient.id === this.props.partner.id ? 'highlight' : '';
        }
    }
    ClientLine.template = 'ClientLine';

    Registries.Component.add(ClientLine);

    return ClientLine;
});
