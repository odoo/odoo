/** @odoo-module **/

import { registry } from "@web/core/registry";
import { PosSelf } from "../../utils/tour_utils";

registry.category("web_tour.tours").add("kiosk_order_tour_takeaway", {
    test: true,
    steps: () => [
        PosSelf.action.clickPrimaryBtn("TOUCH TO START"),
        PosSelf.action.selectLocation("Eat In"),
        ...PosSelf.action.clicKioskProduct("Monitor Stand"),
        PosSelf.action.clickPrimaryBtn("Review Order"),
        PosSelf.check.isKioskOrderline("Monitor Stand", "3.67", 1),
        PosSelf.action.clickPrimaryBtn("Pay at counter"),
        ...PosSelf.action.pressNumpad("1"),
        PosSelf.action.clickPrimaryBtn("Pay"),
        PosSelf.check.isTableNumber("1"),
        PosSelf.check.isPreparingOrder(),

        PosSelf.action.clickPrimaryBtn("Close"),

        PosSelf.action.clickPrimaryBtn("TOUCH TO START"),
        PosSelf.action.selectLocation("Take Out"),
        ...PosSelf.action.clicKioskProduct("Monitor Stand"),
        PosSelf.action.clickPrimaryBtn("Review Order"),
        PosSelf.check.isKioskOrderline("Monitor Stand", "3.67", 1),
        PosSelf.action.clickPrimaryBtn("Pay"),
        PosSelf.check.isPreparingOrder(),
    ],
});
