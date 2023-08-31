/** @odoo-module **/

import { registry } from "@web/core/registry";
import { PosSelf } from "../../utils/tour_utils";

registry.category("web_tour.tours").add("kiosk_order_tour_takeaway", {
    test: true,
    steps: () => [
        PosSelf.action.clickPrimaryBtn('TOUCH TO START'),
        PosSelf.action.selectLocation('Eat In'),
        ...PosSelf.action.clicKioskProduct("Whiteboard Pen"),
        PosSelf.action.clickPrimaryBtn("Review Order"),
        PosSelf.check.isKioskOrderline("Whiteboard Pen", "1.38", 1),
        PosSelf.action.clickPrimaryBtn("Pay"),
        ...PosSelf.action.pressNumpad("1"),
        PosSelf.action.clickPrimaryBtn("Pay"),
        PosSelf.check.isTableNumber(1),
        PosSelf.check.isPreparingOrder(),

        PosSelf.action.clickPrimaryBtn("Close"),

        PosSelf.action.clickPrimaryBtn('TOUCH TO START'),
        PosSelf.action.selectLocation('Take Out'),
        ...PosSelf.action.clicKioskProduct("Whiteboard Pen"),
        PosSelf.action.clickPrimaryBtn("Review Order"),
        PosSelf.check.isKioskOrderline("Whiteboard Pen", "1.38", 1),
        PosSelf.action.clickPrimaryBtn("Pay"),
        PosSelf.check.isPreparingOrder(),
    ],
});
