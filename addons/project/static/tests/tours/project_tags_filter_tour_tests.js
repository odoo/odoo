/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

function changeFilter(filterName) {
    return [
        {
            trigger: ".o_control_panel_actions .o_searchview_dropdown_toggler",
            content: "open searchview menu",
            run: "click",
        },
        {
            trigger: `.o_favorite_menu .dropdown-item span:contains("${filterName}")`,
            run: "click",
        },
        {
            trigger: ".o_control_panel_actions .o_searchview_dropdown_toggler",
            content: "close searchview menu",
            run: "click",
        },
    ];
}

registry.category("web_tour.tours").add("project_tags_filter_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
            run: "click",
        },
        ...changeFilter("Corkscrew tail tag filter"),
        {
            trigger:
                '.o_kanban_group:has(.o_kanban_header:has(span:contains("goat"))):not(:has(.o_kanban_record))',
            content: "check that the corkscrew tail filter has taken effect",
        },
        {
            trigger:
                '.o_kanban_group:has(.o_kanban_header:has(span:contains("pig"))) .o_kanban_record:has(span:contains("Pigs"))',
            content: "check that the corkscrew tail filter has taken effect",
        },
        ...changeFilter("horned tag filter"),
        {
            trigger:
                '.o_kanban_group:has(.o_kanban_header:has(span:contains("pig"))):not(:has(.o_kanban_record))',
            content: "check that the horned filter has taken effect",
        },
        {
            trigger:
                '.o_kanban_group:has(.o_kanban_header:has(span:contains("goat"))) .o_kanban_record:has(span:contains("Goats"))',
            content: "check that the horned filter has taken effect",
        },
        ...changeFilter("4 Legged tag filter"),
        {
            trigger:
                '.o_kanban_group:has(.o_kanban_header:has(span:contains("pig"))) .o_kanban_record:has(span:contains("Pigs"))',
            content: "check that the 4 legged filter has taken effect",
        },
        {
            trigger:
                '.o_kanban_group:has(.o_kanban_header:has(span:contains("goat"))) .o_kanban_record:has(span:contains("Goats"))',
            content: "check that the 4 legged filter has taken effect",
        },
    ],
});
