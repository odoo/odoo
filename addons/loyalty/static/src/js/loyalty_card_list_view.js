/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";

export const LoyaltyCardListView = {
    ...listView,
    buttonTemplate: "loyalty.LoyaltyCardListView.buttons",
};

registry.category("views").add("loyalty_card_list_view", LoyaltyCardListView);
