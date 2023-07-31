/** @odoo-module **/

import { Chrome } from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import { ProductScreen } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("chrome_without_cash_move_permission", {
    test: true,
    url: "/pos/ui",
    steps: () => {
        startSteps();

        ProductScreen.do.confirmOpeningPopup();
        Chrome.do.clickMenuButton();
        Chrome.check.isCashMoveButtonHidden();

        return getSteps();
    },
});
