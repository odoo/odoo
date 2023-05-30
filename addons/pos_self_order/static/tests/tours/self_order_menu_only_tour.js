/** @odoo-module **/

import { registry } from "@web/core/registry";
import { PosSelf } from "./tour_utils";

registry.category("web_tour.tours").add("self_order_menu_only_tour", {
    test: true,
    steps: [
        PosSelf.check.isNotPrimaryBtn("My Orders"),
        PosSelf.check.isPrimaryBtn("View Menu"),
        PosSelf.action.clickPrimaryBtn("View Menu"),
        ...PosSelf.check.cannotAddProduct("Office Chair"),
        PosSelf.action.clickBack(),
        ...PosSelf.check.cannotAddProduct("Office Chair Black"),
        PosSelf.action.clickBack(),
        ...PosSelf.check.cannotAddProduct("Conference Chair (Aluminium)"),
        PosSelf.action.clickBack(),
        PosSelf.check.isNotPrimaryBtn("Review"),
    ],
});
