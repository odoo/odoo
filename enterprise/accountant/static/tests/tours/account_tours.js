/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { accountTourSteps } from "@account/js/tours/account";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

patch(accountTourSteps, {
    goToAccountMenu(description="Open Accounting Menu") {
        return stepUtils.goToAppSteps('accountant.menu_accounting', description);
    }
});
