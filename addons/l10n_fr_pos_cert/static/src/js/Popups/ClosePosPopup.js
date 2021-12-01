odoo.define('l10n_fr_pos_cert.ClosePosPopup', function (require) {
    'use strict';

    const ClosePosPopup = require('point_of_sale.ClosePosPopup');
    const Registries = require('point_of_sale.Registries');

    const PosFrCertClosePopup = (ClosePosPopup) =>
        class extends ClosePosPopup {
            sessionIsOutdated() {
                let isOutdated = false;
                if (this.env.pos.is_french_country() && this.env.pos.pos_session.start_at) {
                    const now = Date.now();
                    let limitDate = new Date(this.env.pos.pos_session.start_at);
                    limitDate.setDate(limitDate.getDate() + 1);
                    isOutdated = limitDate < now;
                }
                return isOutdated;
            }
            canCancel() {
                return super.canCancel() && !this.sessionIsOutdated();
            }
        };

    Registries.Component.extend(ClosePosPopup, PosFrCertClosePopup);

    return ClosePosPopup;
});
