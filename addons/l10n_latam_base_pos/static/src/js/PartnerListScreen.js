odoo.define('l10n_latam_pos.PartnerListScreen', function (require) {
    'use strict';

    const PartnerListScreen = require('point_of_sale.PartnerListScreen');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require("@web/core/utils/hooks");

    const LatamPartnerListScreen = PartnerListScreen =>
        class extends PartnerListScreen {
        /*
        * Setup l10n_latam_identification_type_id
        */
        setup() {
            super.setup();
            useListener('create-new-client', this.createPartner);
        }
    };

    Registries.Component.extend(PartnerListScreen, LatamPartnerListScreen);

    return PartnerListScreen;
});
