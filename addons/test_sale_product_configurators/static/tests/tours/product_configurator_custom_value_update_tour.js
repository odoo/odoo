/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import configuratorTourUtils from "@sale/js/tours/product_configurator_tour_utils";
import tourUtils from "@sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('sale_product_configurator_custom_value_update_tour', {
    url: '/odoo',
    steps: () => [
        ...stepUtils.goToAppSteps("sale.sale_menu_root", "Go to the Sales App"),
        ...tourUtils.createNewSalesOrder(),
        ...tourUtils.selectCustomer("Tajine Saucisse"),
        ...tourUtils.addProduct("Customizable Desk (TEST)"),
        ...configuratorTourUtils.selectAndSetCustomAttribute("Customizable Desk (TEST)", "Legs", "Custom", "123"),
        configuratorTourUtils.assertProductNameContains("Customizable Desk (TEST) (Custom, White)"),
        ...configuratorTourUtils.saveConfigurator(),
        tourUtils.checkSOLDescriptionContains("Customizable Desk (TEST) (Custom, White)", "Legs: Custom: 123"),
        ...stepUtils.saveForm(),
        tourUtils.editLineMatching("Customizable Desk (TEST) (Custom, White)", "Legs: Custom: 123"),
        tourUtils.editConfiguration(),
        configuratorTourUtils.setCustomAttribute("Customizable Desk (TEST)", "Legs", "123456"),
        ...configuratorTourUtils.saveConfigurator(),
        tourUtils.checkSOLDescriptionContains("Customizable Desk (TEST) (Custom, White)", "Legs: Custom: 123456"),
        ...stepUtils.saveForm(),
    ],
});
