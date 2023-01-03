/* @odoo-module */

import PosPopupController from "@point_of_sale/js/Popups/PosPopupController";
import Registries from "@point_of_sale/js/Registries";
import { useBus } from "@web/core/utils/hooks";

export const PosResPopupController = (PosPopupController) =>
    class extends PosPopupController {
        setup() {
            super.setup();
            useBus(this.env.posbus, "close-popups-but-error", this._closePopupsButError);
        }
        _closePopupsButError(event) {
            const { resolve } = event.detail;
            const isErrorPopupOpen = this.popups.some((popup) =>
                popup.name.toLowerCase().includes("error")
            );
            if (!isErrorPopupOpen) {
                for (const popup of this.popups) {
                    popup.props.resolve(false);
                }
                this.popups.length = 0; // clearing the array but keep the useState
            }
            resolve(!isErrorPopupOpen);
        }
    };

Registries.Component.extend(PosPopupController, PosResPopupController);
