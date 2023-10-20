/** @odoo-module **/

import { registry } from "@web/core/registry";
import { PosSelf } from "./tour_utils";

registry.category("web_tour.tours").add("self_order_menu_only_tour", {
    test: true,
    steps: () => [
        PosSelf.isNotPrimaryBtn("My Orders"),
        PosSelf.isPrimaryBtn("View Menu"),
        PosSelf.action.clickPrimaryBtn("View Menu"),
        ...PosSelf.cannotAddProduct("Office Chair"),
        PosSelf.action.clickBack(),
        ...PosSelf.cannotAddProduct("Office Chair Black"),
        PosSelf.action.clickBack(),
        ...PosSelf.cannotAddProduct("Conference Chair (Aluminium)"),
        PosSelf.action.clickBack(),
        PosSelf.isNotPrimaryBtn("Review"),
    ],
});
