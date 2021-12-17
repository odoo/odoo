odoo.define('point_of_sale.PartnerLine', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class PartnerLine extends PosComponent {
        get highlight() {
            return this._isPartnerSelected ? 'highlight' : '';
        }
        get shortAddress() {
            const { partner } = this.props;
            return [partner.zip, partner.city, partner.state_id[1]].filter(field => field).join(', ');
        }
        get _isPartnerSelected() {
            return this.props.partner === this.props.selectedPartner;
        }
    }
    PartnerLine.template = 'PartnerLine';

    Registries.Component.add(PartnerLine);

    return PartnerLine;
});
