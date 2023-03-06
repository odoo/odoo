odoo.define('l10n_latam_pos.models', function (require) {

    const { PosGlobalState } = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');

    const LatamPosGlobalState = (PosGlobalState) => class LatamPosGlobalState extends PosGlobalState {
        //Load l10n_latam.identification.type into vat_types pos attribute
        async _processData(loadedData) {
            await super._processData(...arguments);
            this.vat_types = loadedData['l10n_latam.identification.type'];
        }
    }
    Registries.Model.extend(PosGlobalState, LatamPosGlobalState);

    return PosGlobalState;

});
