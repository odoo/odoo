import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";
import configuratorTourUtils from "@sale/js/tours/product_configurator_tour_utils";
import tourUtils from "@sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("product_attribute_multi_type", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps("sale.sale_menu_root", "Go to the Sales App"),
        ...tourUtils.createNewSalesOrder(),
        ...tourUtils.selectCustomer("Test Partner"),
        ...tourUtils.addProduct("Big Burger"),
        configuratorTourUtils.selectAttribute("Big Burger", "Toppings", "Cheese", "multi"),
        ...configuratorTourUtils.saveConfigurator(),
        ...stepUtils.saveForm(),
    ],
});
