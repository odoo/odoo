odoo.define('l10n_fr_pos_cert.Chrome', function (require) {
    'use strict';

    const Chrome = require('point_of_sale.Chrome');
    const Registries = require('point_of_sale.Registries');

    const PosFrCertChrome = (Chrome) =>
        class extends Chrome {
            async start() {
                await super.start();
                if (this.env.pos.is_french_country() && this.env.pos.pos_session.start_at) {
                    const now = Date.now();
                    let limitDate = new Date(this.env.pos.pos_session.start_at);
                    limitDate.setDate(limitDate.getDate() + 1);
                    if (limitDate < now) {
                        const info = await this.env.pos.getClosePosInfo();
                        this.showPopup('ClosePosPopup', { info: info });
                    }
                }
            }
        };

    Registries.Component.extend(Chrome, PosFrCertChrome);

    return Chrome;
});
