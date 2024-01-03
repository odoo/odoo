/** @odoo-module **/

import * as Chrome from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import * as Dialog from "@point_of_sale/../tests/tours/helpers/DialogTourMethods";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("chrome_without_cash_move_permission", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            Chrome.clickMenuButton(),
            Chrome.isCashMoveButtonHidden(),
        ].flat(),
});
