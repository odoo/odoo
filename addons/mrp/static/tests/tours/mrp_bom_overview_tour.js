/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("test_bom_overview_tour", {
    url: "/web",
    test: true,
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="mrp.menu_mrp_root"]',
        },
        {
            trigger: '.dropdown-toggle[data-menu-xmlid="mrp.menu_mrp_bom"]',
        },
        {
            trigger: '.dropdown-item[data-menu-xmlid="mrp.menu_mrp_bom_form_action"]',
        },
        {
            trigger: 'td.o_data_cell:contains("finish")',
        },
        {
            trigger: 'div.o_stat_info:contains("BoM Overview")',
        },
        {
            trigger: 'table>tbody>tr>td>div>a:contains("finish")',
            extra_trigger: 'h2>a:contains("finish")',
            isCheck: true,
        },
        {
            trigger: 'table>tbody>tr:nth-child(1)>td:nth-child(6)>span:contains("$ 50.00")',
            isCheck: true,
        },
        {
            trigger: 'div.o_control_panel_navigation>div>div>div>button',
        },
        {
            trigger: 'div.o_popover>span:contains("Availabilities")',
        },
        {
            trigger: 'table>tbody>tr:nth-child(1)>td:nth-child(9)>span:contains("$ 50.00")',
            isCheck: true,
        },
        {
            trigger: 'input[id="bom_quantity"]',
            run: 'text 2',
        },
        {
            trigger: 'table>tbody>tr:nth-child(1)>td:nth-child(9)>span:contains("$ 100.00")',
            isCheck: true,
        },
        {
            trigger: 'table>tbody>tr:nth-child(1)>td:nth-child(8):contains("$ 70.00")',
            isCheck: true,
        },
        {
            trigger: 'table>tbody>tr:nth-child(1)>td>span:contains("Not Available")',
            isCheck: true,
        },
        {
            trigger: 'table>tbody>tr:nth-child(2)>td:nth-child(2):contains("4.00")',
            isCheck: true,
        },
    ],
});
