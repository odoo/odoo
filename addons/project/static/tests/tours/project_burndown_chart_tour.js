/** @odoo-module */

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('burndown_chart_tour', {
    url: '/odoo',
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
    run: "click",
}, {
    content: 'Open "Burndown Chart Test" project menu',
            trigger: ".o_kanban_record:contains(Burndown Chart Test)",
    run: `hover && click .o_kanban_record:contains(Burndown Chart Test) .o_dropdown_kanban .dropdown-toggle`,
}, {
    content: `Open "Burndown Chart Test" project's "Burndown Chart" view`,
    trigger: '.o_kanban_manage_reporting div[role="menuitem"] a:contains("Burndown Chart")',
    run: "click",
},
{
    trigger: ".o_graph_renderer",
},
{
    content: 'The sort buttons are not rendered',
    trigger: '.o_graph_renderer:not(:has(.btn-group[role=toolbar][aria-label="Sort graph"]))',
    run: "click",
}, {
    content: 'Remove the project search "Burndown Chart Test"',
    trigger: ".o_searchview_facet:contains(Burndown Chart Test)",
    run: "hover && click .o_facet_remove",
}, {
    content: 'Search Burndown Chart',
    trigger: 'input.o_searchview_input',
    run: `edit Burndown`,
}, {
    content: 'Validate search',
    trigger: '.o_searchview_autocomplete .o_menu_item:contains("Project")',
    run: "click",
}, {
    content: 'Remove the group by "Date: Month > Stage"',
    trigger: '.o_searchview_facet:contains("Stage") .o_facet_remove',
    run: "click",
}, {
    content: 'A "The Burndown Chart must be grouped by Date and Stage" notification is shown when trying to remove the group by "Date: Month > Stage"',
    trigger: '.o_notification_manager .o_notification:contains("The report should be grouped either by ") button.o_notification_close',
    run: "click",
}, {
    content: 'Open the search panel menu',
    trigger: '.o_control_panel .o_searchview_dropdown_toggler',
    run: "click",
}, {
    content: 'The Stage group menu item is visible',
    trigger: '.o_group_by_menu .o_menu_item:contains("Stage")',
    run: "click",
}, {
    content: 'Open the Date group by sub menu',
    trigger: '.o_group_by_menu button.o_menu_item:contains("Date")',
    run: "click",
}, {
    content: 'Click on the selected Date sub menu',
    trigger: '.o_group_by_menu button.o_menu_item:contains("Date") + * .dropdown-item.selected',
    run: "click",
}, {
    content: 'A "The Burndown Chart must be grouped by Date" notification is shown when trying to remove the group by "Date: Month > Stage"',
    trigger: '.o_notification_manager .o_notification:contains("The Burndown Chart must be grouped by Date") button.o_notification_close',
    run: "click",
}, {
    content: 'Open the search panel menu',
    trigger: '.o_control_panel .o_searchview_dropdown_toggler',
    run: "click",
}, {
    content: 'Open the Date filter sub menu',
    trigger: '.o_filter_menu button.o_menu_item:contains("Date")',
    run: "click",
}, {
    content: 'Click on the first Date filter sub menu',
    trigger: '.o_filter_menu .o_menu_item:contains("Date") + * .dropdown-item:first-child',
    run: "click",
}, {
    content: 'Close the Date filter menu',
    trigger: '.o_graph_renderer',
    run: "click",
}, {
    content: 'Open the search panel menu',
    trigger: '.o_control_panel .o_searchview_dropdown_toggler',
    run: "click",
}, {
    content: 'The comparison menu is not rendered',
    trigger: ':not(:has(.o_comparison_menu))',
}]});
