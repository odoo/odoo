odoo.define('point_of_sale.ClientDetails', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');

    class ClientDetails extends PosComponent {
        static template = 'ClientDetails';
        get partnerImageUrl() {
            if (this.props.partner) {
                return `/web/image?model=res.partner&id=${this.props.partner.id}&field=image_128`;
            } else {
                return false;
            }
        }
    }

    return { ClientDetails };
});
