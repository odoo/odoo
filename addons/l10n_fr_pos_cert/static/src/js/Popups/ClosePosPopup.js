/** @odoo-module */

import ClosePosPopup from "@point_of_sale/js/Popups/ClosePosPopup";
import Registries from "@point_of_sale/js/Registries";

const PosFrCertClosePopup = (ClosePosPopup) =>
    class extends ClosePosPopup {
        sessionIsOutdated() {
            let isOutdated = false;
            if (this.env.pos.is_french_country() && this.env.pos.pos_session.start_at) {
                const now = Date.now();
                const limitDate = new Date(this.env.pos.pos_session.start_at);
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

export default ClosePosPopup;
