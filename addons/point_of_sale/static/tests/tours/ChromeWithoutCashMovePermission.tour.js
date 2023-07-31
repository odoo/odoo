/** @odoo-module **/

import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import { Chrome } from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import { registry } from "@web/core/registry";

startSteps();

Chrome.do.clickMenuButton();
Chrome.check.isCashMoveButtonHidden();

registry
    .category("web_tour.tours")
    .add("chrome_without_cash_move_permission", { test: true, url: "/pos/ui", steps: getSteps() });
