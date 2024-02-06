/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import configuratorTourUtils from "@test_sale_product_configurators/js/tour_utils";

registry.category("web_tour.tours").add('sale_product_configurator_custom_value_update_tour', {
    url: '/web',
    test: true,
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
}, {
    trigger: '.o_list_button_add',
    extra_trigger: '.o_sale_order',
}, {
    trigger: '.o_required_modifier[name=partner_id] input',
    run: 'text Tajine Saucisse',
}, {
    trigger: '.ui-menu-item > a:contains("Tajine Saucisse")',
    auto: true,
}, {
    trigger: 'a:contains("Add a product")'
}, {
    trigger: 'div[name="product_template_id"] input',
    run: 'text Custo',
}, {
    trigger: 'ul.ui-autocomplete a:contains("Customizable Desk (TEST)")',
},
...configuratorTourUtils.selectAndSetCustomAttribute("Customizable Desk (TEST)", "Legs", "Custom", "123"),
configuratorTourUtils.assertProductNameContains("Customizable Desk (TEST) (Custom, White)"),
{
    trigger: 'button:contains(Confirm)',
}, {
    trigger: 'td.o_data_cell:contains("Legs: Custom: 123")',
    isCheck: true,
},
...stepUtils.saveForm(),
{
    trigger: 'td.o_data_cell:contains("Legs: Custom: 123")',
    isCheck: true,
},
{
    trigger: 'div[name="product_template_id"]',
}, {
    trigger: '.fa-pencil',
    extra_trigger: '.o_external_button',
},
configuratorTourUtils.setCustomAttribute("Customizable Desk (TEST)", "Legs", "123456"),
{
    trigger: 'button:contains(Confirm)',
}, {
    trigger: 'td.o_data_cell:contains("Legs: Custom: 123456")',
    isCheck: true,
},
...stepUtils.saveForm(),
]});
