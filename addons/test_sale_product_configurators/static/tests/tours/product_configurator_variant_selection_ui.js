import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";
import * as tourUtils from "@sale/js/tours/tour_utils";
import configuratorTourUtils from "@sale/js/tours/product_configurator_tour_utils";

registry.category("web_tour.tours").add('sale_product_configurator_variant_selection_tour', {
    steps: () => [
        ...stepUtils.goToAppSteps("sale.sale_menu_root", "Go to the Sales App"),
        ...tourUtils.createNewSalesOrder(),
        ...tourUtils.selectCustomer("Tajine Saucisse"),
        {
            content: "Show the optional columns",
            trigger: ".o_optional_columns_dropdown_toggle",
            run: "click",
        },
        {
            content: "Show the Product Variant column",
            trigger: '.o-dropdown--menu .dropdown-item:contains("Product Variant")',
            run: "click",
        },
        {
            content: "Create a new order line",
            trigger: 'button:contains("Add Line")',
            run: "click",
        },
        {
            content: "Search for a product variant",
            trigger: '.o_selected_row .o_field_widget[name="product_id"] input',
            run: "edit Customizable Desk",
        },
        {
            content: "Select the Steel, White variant",
            trigger: 'ul.ui-autocomplete a:contains("Steel, White")',
            run: "click",
        },
        // The configurator opens to suggest the optional products of the selected variant
        configuratorTourUtils.assertProductNameContains("Customizable Desk (TEST)"),
        {
            content: "Assert that the optional product is suggested",
            trigger: configuratorTourUtils.optionalProductSelector("Chair floor protection"),
        },
        {
            content: "Assert that the selected variant's attributes can't be changed",
            trigger: `
                table.o_sale_product_configurator_table:not(.o_sale_product_configurator_table_optional):not(:has(div[name="ptal"]))
            `,
        },
        {
            content: "Assert that the optional products' attributes can still be configured",
            trigger: `
                ${configuratorTourUtils.optionalProductSelector("Conference Chair")}
                div[name="ptal"]
            `,
        },
        {
            content: "Discard the configurator",
            trigger: '.o_sale_product_configurator_dialog button:contains("Discard")',
            run: "click",
        },
        {
            content: "Wait until the modal is closed",
            trigger: 'body:not(:has(.o_sale_product_configurator_dialog))',
        },
        ...tourUtils.clickSomewhereElse(),
        {
            content: "Assert that the variant was kept on the order line",
            trigger: 'td[name="product_id"]:contains("Steel, White")',
        },
        {
            content: "Edit the order line product variant",
            trigger: 'td[name="product_id"]:contains("Steel, White")',
            run: "click",
        },
        {
            content: "Search for another product variant",
            trigger: '.o_selected_row .o_field_widget[name="product_id"] input',
            run: "edit Customizable Desk",
        },
        {
            content: "Select the Aluminium, White variant",
            trigger: 'ul.ui-autocomplete a:contains("Aluminium, White")',
            run: "click",
        },
        configuratorTourUtils.addOptionalProduct("Chair floor protection"),
        ...configuratorTourUtils.saveConfigurator(),
        ...tourUtils.clickSomewhereElse(),
        {
            content: "Assert that the new variant is on the order line",
            trigger: 'td[name="product_id"]:contains("Aluminium, White")',
        },
        {
            content: "Assert that the optional product was added",
            trigger: 'td[name="product_id"]:contains("Chair floor protection")',
        },
        ...stepUtils.saveForm(),
    ],
});
