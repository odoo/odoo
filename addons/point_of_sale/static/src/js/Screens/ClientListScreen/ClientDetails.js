odoo.define('point_of_sale.ClientDetails', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class ClientDetails extends PosComponent {
        get partnerImageUrl() {
            const partner = this.props.partner;
            if (partner) {
                return `/web/image?model=res.partner&id=${partner.id}&field=image_128&write_date=${partner.write_date}&unique=1`;
            } else {
                return false;
            }
        }
    }
    ClientDetails.template = 'ClientDetails';

    Registries.Component.add(ClientDetails);

    return ClientDetails;
});
