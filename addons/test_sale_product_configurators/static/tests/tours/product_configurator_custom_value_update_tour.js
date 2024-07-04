/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import configuratorTourUtils from "@sale/js/tours/product_configurator_tour_utils";

registry.category("web_tour.tours").add('sale_product_configurator_custom_value_update_tour', {
    url: '/web',
    test: true,
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    run: "click",
}, 
{
    trigger: ".o_sale_order",
},
{
    trigger: '.o_list_button_add',
    run: "click",
}, {
    trigger: '.o_required_modifier[name=partner_id] input',
    run: "edit Tajine Saucisse",
}, {
    isActive: ["auto"],
    trigger: '.ui-menu-item > a:contains("Tajine Saucisse")',
    run: "click",
}, {
    trigger: 'a:contains("Add a product")',
    run: "click",
}, {
    trigger: 'div[name="product_template_id"] input',
    run: "edit Custo",
}, {
    trigger: 'ul.ui-autocomplete a:contains("Customizable Desk (TEST)")',
    run: "click",
},
...configuratorTourUtils.selectAndSetCustomAttribute("Customizable Desk (TEST)", "Legs", "Custom", "123"),
configuratorTourUtils.assertProductNameContains("Customizable Desk (TEST) (Custom, White)"),
{
    trigger: ".modal button:contains(Confirm)",
    in_modal: false,
    run: "click",
}, {
    trigger: 'td.o_data_cell:contains("Legs: Custom: 123")',
},
...stepUtils.saveForm(),
{
    trigger: 'td.o_data_cell:contains("Legs: Custom: 123")',
},
{
    trigger: 'div[name="product_template_id"]',
    run: "click",
}, 
{
    trigger: ".o_external_button",
},
{
    trigger: '.fa-pencil',
    run: "click",
},
configuratorTourUtils.setCustomAttribute("Customizable Desk (TEST)", "Legs", "123456"),
{
    trigger: ".modal button:contains(Confirm)",
    in_modal: false,
    run: "click",
}, {
    trigger: 'td.o_data_cell:contains("Legs: Custom: 123456")',
},
...stepUtils.saveForm(),
]});
