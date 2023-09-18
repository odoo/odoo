/** @odoo-module **/

import { registry } from "@web/core/registry";
import { PosSelf } from "../../utils/tour_utils";

registry.category("web_tour.tours").add("kiosk_order_tour_table_service", {
    test: true,
    steps: () => [
        PosSelf.action.clickPrimaryBtn("TOUCH TO START"),
        ...PosSelf.action.clicKioskProduct("Monitor Stand"),
        PosSelf.action.clickPrimaryBtn("Review Order"),
        PosSelf.check.isKioskOrderline("Monitor Stand", "3.67", 1),
        PosSelf.action.clickPrimaryBtn("Pay"),
        ...PosSelf.action.pressNumpad("2"),
        PosSelf.action.clickPrimaryBtn("Pay"),
        PosSelf.check.isTableNumber("2"),
        PosSelf.check.isPreparingOrder(),
        PosSelf.action.clickPrimaryBtn("Close"),
    ],
});
