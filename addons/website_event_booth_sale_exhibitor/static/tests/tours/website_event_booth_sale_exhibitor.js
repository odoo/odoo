/** @odoo-module **/

import { registry } from "@web/core/registry";
import registerSteps from "website_event_booth_exhibitor.tour_utils";
import tourUtils from "website_sale.tour_utils";

registry.category("web_tour.tours").add("weboothsale_exhibitor_register", {
    test: true,
    url: "/event",
    steps: [
        ...registerSteps,
        tourUtils.goToCheckout(),
        ...tourUtils.payWithTransfer(),
    ]
});
