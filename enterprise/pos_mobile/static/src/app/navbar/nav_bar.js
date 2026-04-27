import mobile from "@web_mobile/js/services/core";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(Navbar.prototype, {
    setup() {
        super.setup();
        if (this.supportDualDisplay) {
            mobile.methods.getDisplays({ onlyPresentation: true }).then((result) => {
                if (!result.success || !result.data) {
                    return;
                }
                /**
                 * @typedef {Object} Display
                 * @property {number} displayId - The ID of the display.
                 * @property {string} name - The name of the display.
                 */

                /** @type {Display[]} */
                const displays = result.data;
                displays.forEach((display) => {
                    mobile.methods
                        .showDisplayAndGoToUrl({
                            url: "about:blank",
                            displayId: display.displayId,
                        })
                        .catch((error) => {
                            console.error("Error opening customer display", error);
                        });
                });
            });
        }
    },
    get customerFacingDisplayButtonIsShown() {
        return this.supportDualDisplay || super.customerFacingDisplayButtonIsShown;
    },
    get supportDualDisplay() {
        return mobile.methods.getDisplays && this.pos.config.customer_display_type === "local";
    },
    openCustomerDisplay() {
        if (!this.supportDualDisplay) {
            super.openCustomerDisplay();
            return;
        }
        mobile.methods
            .getDisplays({ onlyPresentation: true })
            .then((result) => {
                if (!result.success || !result.data) {
                    this.notification.add(_t("Dual display is not supported on this device"));
                    return;
                }

                /**
                 * @typedef {Object} Display
                 * @property {number} displayId - The ID of the display.
                 * @property {string} name - The name of the display.
                 */

                /** @type {Display[]} */
                const displays = result.data;
                if (displays.length === 1) {
                    this._showDisplayAndGoToUrl({ displayId: displays[0].displayId });
                } else {
                    makeAwaitable(this.dialog, SelectionPopup, {
                        list: displays.map((display) => ({
                            id: display.displayId,
                            label: display.name,
                            isSelected: false,
                            item: display,
                        })),
                        title: _t("Select a display"),
                    }).then((selectedDisplay) => {
                        if (!selectedDisplay) {
                            return;
                        }
                        this._showDisplayAndGoToUrl({
                            displayId: selectedDisplay.displayId,
                        });
                    });
                }
            })
            .catch((error) => {
                console.error("Error opening customer display:", error);
                this.notification.add(_t("An error occurred while opening the display."));
            });
    },
    _showDisplayAndGoToUrl({ displayId }) {
        mobile.methods
            .showDisplayAndGoToUrl({
                url: `${this.pos.session._base_url}/pos_customer_display/${this.pos.config.id}/${this.pos.config.access_token}`,
                displayId: displayId,
            })
            .catch((error) => {
                console.error("Error opening customer display");
                this.notification.add(_t("An error occurred while opening the display."));
            });
    },
});
