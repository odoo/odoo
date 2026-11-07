/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { useService } from "@web/core/utils/hooks";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class TableGuestsButton extends Component {
    static template = "pos_restaurant.TableGuestsButton";

    setup() {
        this.pos = usePos();
        this.popup = useService("popup");
    }
    get currentOrder() {
        return this.pos.get_order();
    }
    get nGuests() {
        return this.currentOrder ? this.currentOrder.getCustomerCount() : 0;
    }
    async click() {
        const { confirmed, payload: inputNumber } = await this.popup.add(NumberPopup, {
            startingValue: this.nGuests,
            cheap: true,
            title: _t("Guests?"),
            isInputSelected: true,
        });

        if (confirmed) {
            const guestCount = parseInt(inputNumber, 10) || 0;
            // Set the maximum number possible for an integer
            const max_capacity = 2 ** 31 - 1;
            if (guestCount > max_capacity) {
                await this.popup.add(ErrorPopup, {
                    title: _t("Blocked action"),
                    body: _t("You cannot put a number that exceeds %s ", max_capacity),
                });
                return;
            }

            if (guestCount == 0 && this.currentOrder.orderlines.length === 0) {
                this.pos.removeOrder(this.currentOrder);
                this.pos.showScreen("FloorScreen");
            }

            this.currentOrder.setCustomerCount(guestCount);
        }
    }
}

ProductScreen.addControlButton({
    component: TableGuestsButton,
    condition: function () {
        return this.pos.config.module_pos_restaurant;
    },
});
