/** @odoo-module */

import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { useService } from "@web/core/utils/hooks";
import { NumberPopup } from "@point_of_sale/js/Popups/NumberPopup";
import { ErrorPopup } from "@point_of_sale/js/Popups/ErrorPopup";
import { Component } from "@odoo/owl";

export class TableGuestsButton extends Component {
    static template = "TableGuestsButton";

    setup() {
        super.setup();
        this.popup = useService("popup");
    }
    get currentOrder() {
        return this.env.pos.get_order();
    }
    get nGuests() {
        return this.currentOrder ? this.currentOrder.getCustomerCount() : 0;
    }
    async click() {
        const { confirmed, payload: inputNumber } = await this.popup.add(NumberPopup, {
            startingValue: this.nGuests,
            cheap: true,
            title: this.env._t("Guests ?"),
            isInputSelected: true,
        });

        if (confirmed) {
            const guestCount = parseInt(inputNumber, 10) || 1;
            // Set the maximum number possible for an integer
            const max_capacity = 2 ** 31 - 1;
            if (guestCount > max_capacity) {
                await this.popup.add(ErrorPopup, {
                    title: this.env._t("Blocked action"),
                    body: _.str.sprintf(
                        this.env._t("You cannot put a number that exceeds %s "),
                        max_capacity
                    ),
                });
                return;
            }
            this.env.pos.get_order().setCustomerCount(guestCount);
        }
    }
}

ProductScreen.addControlButton({
    component: TableGuestsButton,
    condition: function () {
        return this.env.pos.config.module_pos_restaurant;
    },
});
