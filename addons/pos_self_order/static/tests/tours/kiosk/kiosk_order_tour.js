/** @odoo-module **/

import { registry } from "@web/core/registry";
import { PosSelf } from "../../utils/tour_utils";

registry.category("web_tour.tours").add("kiosk_order_tour", {
    test: true,
    steps: () => [
        PosSelf.action.clickPrimaryBtn('TOUCH TO START'),
        PosSelf.action.clickPrimaryBtn("CANCEL ORDER"),
        PosSelf.action.clickCancelPopupBtn(),

        PosSelf.action.clickPrimaryBtn('TOUCH TO START'),
        ...PosSelf.action.clicKioskProduct("Whiteboard Pen"),
        ...PosSelf.action.clicKioskProduct("Large Cabinet"),
        PosSelf.action.clickPrimaryBtn("Review Order"),
        PosSelf.check.isKioskOrderline("Whiteboard Pen", "1.38", 1),
        PosSelf.check.isKioskOrderline("Large Cabinet", "368.00", 1),
        ...PosSelf.action.clickKioskTrash("Large Cabinet"),
        PosSelf.check.isNotKioskOrderline("Large Cabinet"),
        PosSelf.action.clickPrimaryBtn("Pay"),
        PosSelf.check.isPreparingOrder(),
    ],
});
