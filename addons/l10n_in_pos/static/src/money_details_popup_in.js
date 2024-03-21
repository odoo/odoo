/** @odoo-module */

import { useState } from "@odoo/owl";
import { MoneyDetailsPopup } from "@point_of_sale/app/utils/money_details_popup/money_details_popup";
import { patch } from "@web/core/utils/patch";

patch(MoneyDetailsPopup.prototype, {
    setup() {
        super.setup();
        if (this.pos.company.country_id?.code === "IN") {
            const inMoneyDetails = Object.entries(this.state.moneyDetails).reduce(
                (moneyDetails, [amt, cnt]) => {
                    if (parseFloat(amt) >= 1) {
                        moneyDetails[amt] = cnt;
                    }
                    return moneyDetails;
                },
                {}
            );
            this.state = useState({
                moneyDetails: inMoneyDetails,
            });
        }
    },
});
