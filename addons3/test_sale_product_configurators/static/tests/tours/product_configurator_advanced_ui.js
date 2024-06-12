/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils, TourError } from "@web_tour/tour_service/tour_utils";
import configuratorTourUtils from "@test_sale_product_configurators/js/tour_utils";

let optionVariantImage;

registry.category("web_tour.tours").add('sale_product_configurator_advanced_tour', {
    url: '/web',
    test: true,
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
},  {
    trigger: '.o_list_button_add',
    extra_trigger: '.o_sale_order'
}, {
    trigger: '.o_required_modifier[name=partner_id] input',
    run: 'text Tajine Saucisse',
}, {
    trigger: '.ui-menu-item > a:contains("Tajine Saucisse")',
    auto: true,
}, {
    trigger: 'a:contains("Add a product")',
    extra_trigger: '.o_field_widget[name=partner_shipping_id] .o_external_button', // Wait for onchange_partner_id
}, {
    trigger: 'div[name="product_template_id"] input',
    run: 'text Custo',
}, {
    trigger: 'ul.ui-autocomplete a:contains("Customizable Desk (TEST)")',
},
    ...configuratorTourUtils.selectAndSetCustomAttribute("Customizable Desk", "Legs", "Custom", "Custom 1"),
    ...configuratorTourUtils.selectAndSetCustomAttribute("Customizable Desk", "PA1", "PAV9", "Custom 2"),
    configuratorTourUtils.selectAttribute("Customizable Desk", "PA2", "PAV5"),
    ...configuratorTourUtils.selectAndSetCustomAttribute("Customizable Desk", "PA4", "PAV9", "Custom 3", "select"),
    configuratorTourUtils.assertProductNameContains("Custom, White, PAV9, PAV5, PAV1"),
{
    trigger: 'table.o_sale_product_configurator_table_optional tr:has(td>div[name="o_sale_product_configurator_name"] h5:contains("Conference Chair (TEST) (Steel)"))',
    run: function () {
        optionVariantImage = $('table.o_sale_product_configurator_table_optional tr:has(td>div[name="o_sale_product_configurator_name"] h5:contains("Conference Chair (TEST) (Aluminium)")) td[name="o_sale_product_configurator_img"]>img').attr('src');
    }
},
    configuratorTourUtils.selectAttribute("Conference Chair", "Legs", "Aluminium"),
{
    trigger: 'table.o_sale_product_configurator_table_optional tr:has(td>div[name="o_sale_product_configurator_name"] h5:contains("Conference Chair (TEST) (Aluminium)"))',
    run: function () {
        let newVariantImage = $('table.o_sale_product_configurator_table_optional tr:has(td>div[name="o_sale_product_configurator_name"] h5:contains("Conference Chair (TEST) (Aluminium)")) td[name="o_sale_product_configurator_img"]>img').attr('src');
        if (newVariantImage !== optionVariantImage) {
            throw new TourError('image variant option src changed');
        }
    }
}, {
    trigger: 'button:contains(Confirm)',
}, {
    trigger: 'td.o_data_cell:contains("Customizable Desk (TEST) (Custom, White, PAV9, PAV5, PAV1)"):not(:contains("PA9: Single PAV"))',
    isCheck: true,
}, {
    trigger: 'td.o_data_cell:contains("Legs: Custom: Custom 1")',
    isCheck: true,
}, {
    trigger: 'td.o_data_cell:contains("PA1: PAV9: Custom 2")',
    isCheck: true,
}, {
    trigger: 'td.o_data_cell:contains("PA4: PAV9: Custom 3")',
    isCheck: true,
}, {
    trigger: 'td.o_data_cell:contains("PA5: PAV1")',
    isCheck: true,
}, {
    trigger: 'td.o_data_cell:contains("PA7: PAV1")',
    isCheck: true,
}, {
    trigger: 'td.o_data_cell:contains("PA8: PAV1")',
    isCheck: true,
}, ...stepUtils.saveForm()
]});
