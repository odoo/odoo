/** @odoo-module */

import { Product } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { _t } from "@web/core/l10n/translation";


patch(Product.prototype, {
    async _onScaleNotAvailable() {
        await this.env.services.popup.add(ErrorPopup, {
            title: _t("No Scale Detected"),
            body: _t(
                "It seems that no scale was detected.\nMake sure that the scale is connected and visible in the IoT app."
            ),
        });
    },
    get isScaleAvailable() {
        return super.isScaleAvailable && Boolean(this.pos.hardwareProxy.deviceControllers.scale);
    },
});
