/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { popupService } from "@point_of_sale/app/popup/popup_service";

patch(popupService, {
    start() {
        return Object.assign(super.start(...arguments), {
            closePopupsButError() {
                const popups = Object.values(this.popups);
                const isErrorPopupOpen = popups.some((popup) =>
                    // FIXME POSREF: this seems very brittle.
                    popup.component.name.toLowerCase().includes("error")
                );
                if (!isErrorPopupOpen) {
                    for (const popup of popups) {
                        popup.props.close(false);
                    }
                }
                return !isErrorPopupOpen;
            },
        });
    },
});
