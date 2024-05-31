/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils, TourError } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('mrp_product_configurator_tour', {
    url: '/web',
    test: true,
    steps: () => [stepUtils.showAppsMenuItem(), {
        trigger: '.o_app[data-menu-xmlid="mrp.menu_mrp_root"]',
    }, {
        trigger: '.dropdown-toggle[data-menu-xmlid="mrp.menu_mrp_manufacturing"]'
    }, {
        trigger: '.dropdown-item[data-menu-xmlid="mrp.menu_mrp_production_action"]'
    }, {
        trigger: '.o_list_button_add',
    }, {
        trigger: 'input[id="product_tmpl_id_0"]',
        run: 'edit Custo',
    }, {
        trigger: 'ul.ui-autocomplete a:contains("Customizable Desk (TEST)")',
    }, {
        trigger: 'main.modal-body>table:nth-child(1)>tbody label:contains("Steel")',
        isCheck: true,
    }, {
        trigger: 'main.modal-body>table:nth-child(1)>tbody label:contains("Aluminium")',
    }, {
        trigger: 'label[style="background-color:#000000"] input'
    }, {
        trigger: '.btn-primary:disabled:contains("Confirm")',
        isCheck: true, // check confirm button is disabled
    }, {
        trigger: 'label[style="background-color:#FFFFFF"] input'
    }, {
        trigger: '.btn-primary:not(:disabled):contains("Confirm")',
        extra_trigger: '.modal-footer',
        isCheck: true, // check confirm is available
    }, {
        trigger: 'main.modal-body>table:nth-child(1)>tbody label:contains("Custom")',
    }, {
        trigger: `table.o_product_configurator_table td>div[name="ptal"]:has(div>label:contains("Custom")) input[type="text"]`,
        run: `edit Customized Value && click .modal-body`,
    }, {
        trigger: `table.o_product_configurator_table td.o_product_configurator_qty div>button:has(i.fa-plus)`,
    }, {
        content: "add to MO",
        trigger: 'button:contains(Confirm)',
        run: "click",
    }, {
        trigger: 'textarea[id="product_description_0"]',
        run: () => {
            if(document.querySelector("input[id='product_tmpl_id_0']")?.value !== "Customizable Desk (TEST)") {
                throw new TourError("The product template name is incorrect");
            }
            if(document.querySelector("textarea[id='product_description_0']")?.value !== "Customizable Desk (TEST) (Custom, White)\nLegs: Custom: Customized Value"){
                throw new TourError("The product description is incorrect");
            }
            if(document.querySelector("input[id='product_qty_0']")?.value !== "2.00"){
                throw new TourError("The product quantity is incorrect");
            }
        }
    }, {
        trigger: 'button[name="action_confirm"]',
    }, ...stepUtils.saveForm(),
]});
