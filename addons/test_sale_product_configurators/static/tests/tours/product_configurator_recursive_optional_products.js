/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import configuratorTourUtils from "@sale/js/tours/product_configurator_tour_utils";
import tourUtils from "@sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('sale_product_configurator_recursive_optional_products_tour', {
    url: '/odoo',
    steps: () => [
        ...stepUtils.goToAppSteps("sale.sale_menu_root", "Go to the Sales App"),
        ...tourUtils.createNewSalesOrder(),
        ...tourUtils.addProduct("Customizable Desk (TEST)"),
        configuratorTourUtils.selectAttribute("Customizable Desk", "Legs", "Aluminium"),
        configuratorTourUtils.addOptionalProduct("Conference Chair"),
        configuratorTourUtils.addOptionalProduct("Chair floor protection"),
        {
            trigger: ".modal button:contains(Confirm)",
            run: "click",
        },
        ...stepUtils.discardForm(),
    ],
});
