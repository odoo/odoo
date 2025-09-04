import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";
import configuratorTourUtils from "@sale/js/tours/product_configurator_tour_utils";
import tourUtils from "@sale/js/tours/tour_utils";

let optionVariantImage;

registry.category("web_tour.tours").add('sale_product_configurator_advanced_tour', {
    url: '/odoo',
    steps: () => [
        ...stepUtils.goToAppSteps("sale.sale_menu_root", "Go to the Sales App"),
        ...tourUtils.createNewSalesOrder(),
        ...tourUtils.selectCustomer("Tajine Saucisse"),
        {
            trigger: ".o_field_widget[name=partner_shipping_id] .o_external_button:not(:visible)", // Wait for onchange_partner_id
        },
        ...tourUtils.addProduct("Customizable Desk (TEST)"),
        ...configuratorTourUtils.selectAndSetCustomAttribute("Customizable Desk", "Legs", "Custom", "Custom 1"),
        ...configuratorTourUtils.selectAndSetCustomAttribute("Customizable Desk", "PA1", "PAV9", "Custom 2"),
        configuratorTourUtils.selectAttribute("Customizable Desk", "PA2", "PAV5"),
        ...configuratorTourUtils.selectAndSetCustomAttribute("Customizable Desk", "PA4", "PAV9", "Custom 3", "select"),
        configuratorTourUtils.assertProductNameContains("Custom, White, PAV9, PAV5, PAV1"),
        {
            trigger: configuratorTourUtils.optionalProductSelector("Conference Chair (TEST) (Steel)"),
            run({ queryOne }) {
                optionVariantImage = configuratorTourUtils.optionalProductImageSrc(
                    queryOne,
                    "Conference Chair (TEST) (Steel)"
                );
            }
        },
        configuratorTourUtils.selectAttribute("Conference Chair", "Legs", "Aluminium"),
        {
            trigger: configuratorTourUtils.optionalProductSelector("Conference Chair (TEST) (Aluminium)"),
            run({ queryOne }) {
                const newOptionVariantImage = configuratorTourUtils.optionalProductImageSrc(
                    queryOne,
                    "Conference Chair (TEST) (Aluminium)"
                );
                if (newOptionVariantImage === optionVariantImage) {
                    console.error("The variant image wasn't updated");
                }
            }
        },
        ...configuratorTourUtils.saveConfigurator(),
        tourUtils.checkSOLDescriptionContains(
            "Customizable Desk (TEST) (Custom, White, PAV9, PAV5, PAV1)",
            "PA5: PAV1\nPA7: PAV1\nPA8: PAV1\nLegs: Custom: Custom 1\nPA1: PAV9: Custom 2\nPA4: PAV9: Custom 3",
        ),
        ...stepUtils.saveForm(),
    ],
});
