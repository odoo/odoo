/** @odoo-module */

import tour from 'web_tour.tour';

tour.register('burndown_chart_tour', {
    test: true,
    url: '/web',
},
[tour.stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
}, {
    content: 'Open "Burndown Chart Test" project menu',
    trigger: '.o_kanban_record:contains("Burndown Chart Test") .o_kanban_manage_toggle_button',
}, {
    content: `Open "Burndown Chart Test" project's "Burndown Chart" view`,
    trigger: '.o_kanban_record:contains("Burndown Chart Test") .o_kanban_manage_reporting div[role="menuitem"] a:contains("Burndown Chart")',
}, {
    content: 'The sort buttons are not rendered',
    trigger: '.o_cp_bottom_left:not(:has(.btn-group[role=toolbar][aria-label="Sort graph"]))',
    extra_trigger: '.o_graph_renderer',
}, {
    content: 'Remove the project search "Burndown Chart Test"',
    trigger: '.o_searchview_facet:contains("Burndown Chart Test") .o_facet_remove',
}, {
    content: 'Search Burndown Chart',
    trigger: 'input.o_searchview_input',
    run: `text Burndown`,
}, {
    content: 'Validate search',
    trigger: '.o_searchview_autocomplete .o_menu_item:contains("Project")',
}, {
    content: 'Remove the group by "Date: Month > Stage"',
    trigger: '.o_searchview_facet:contains("Date: Month") .o_facet_remove',
}, {
    content: 'A "The Burndown Chart must be grouped by Date and Stage" notification is shown when trying to remove the group by "Date: Month > Stage"',
    trigger: '.o_notification_manager .o_notification:contains("The Burndown Chart must be grouped by Date and Stage") button.o_notification_close',
}, {
    content: 'Open the group by menu',
    trigger: '.o_group_by_menu button',
}, {
    content: 'The Stage group menu item is invisible',
    trigger: '.o_group_by_menu:not(:has(.o_menu_item:contains("Stage")))',
}, {
    content: 'Open the Date group by sub menu',
    trigger: '.o_group_by_menu button.o_menu_item:contains("Date")',
    run: function () {
        this.$anchor[0].dispatchEvent(new Event('mouseenter'));
    },
}, {
    content: 'Click on the selected Date sub menu',
    trigger: '.o_group_by_menu button.o_menu_item:contains("Date") + * .dropdown-item.selected',
    run: function () {
        this.$anchor[0].dispatchEvent(new Event('click'));
    },
}, {
    content: 'A "The Burndown Chart must be grouped by Date" notification is shown when trying to remove the group by "Date: Month > Stage"',
    trigger: '.o_notification_manager .o_notification:contains("The Burndown Chart must be grouped by Date") button.o_notification_close',
}, {
    content: 'Open the filter menu',
    trigger: '.o_filter_menu button',
}, {
    content: 'Open the Date filter sub menu',
    trigger: '.o_filter_menu button.o_menu_item:contains("Date")',
    run: function () {
        this.$anchor[0].dispatchEvent(new Event('mouseenter'));
    },
}, {
    content: 'Click on the first Date filter sub menu',
    trigger: '.o_filter_menu .o_menu_item:contains("Date") + * .dropdown-item:first-child',
    run: function () {
        this.$anchor[0].dispatchEvent(new Event('click'));
    },
}, {
    content: 'Close the Date filter menu',
    trigger: '.o_graph_renderer',
}, {
    content: 'The comparison menu is not rendered',
    trigger: '.o_search_options:not(:has(.o_comparison_menu))',
}]);
