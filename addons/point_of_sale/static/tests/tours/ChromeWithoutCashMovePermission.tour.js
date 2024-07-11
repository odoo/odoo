/** @odoo-module **/

import * as Chrome from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("chrome_without_cash_move_permission", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            Chrome.clickMenuButton(),
            Chrome.isCashMoveButtonHidden(),
        ].flat(),
});
