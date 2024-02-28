/** @odoo-module **/

import tour from 'web_tour.tour';

function changeFilter(filterName) {
    return [
        {
            trigger: '.o_favorite_menu button:has(i.fa-star)',
            content: 'click on the favorite menu',
        },
        {
            trigger: `.o_favorite_menu .dropdown-item span:contains("${filterName}")`,
        },
        {
            trigger: '.o_group_by_menu button:has(i.oi-group)',
            content: 'click on the groupby menu',
            run: function (actions) {
                this.$anchor[0].dispatchEvent(new Event('mouseenter'));
            },
        },
        {
            trigger: '.o_group_by_menu span:contains("Stage")',
            content: 'click on the stage gb',
        },
    ];
}

tour.register('project_tags_filter_tour',
    {
        test: true,
        url: '/web',
    },
    [
    tour.stepUtils.showAppsMenuItem(),
    {
        trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
    }, ...changeFilter("Corkscrew tail tag filter"),
    {
        trigger: '.o_kanban_group:has(.o_kanban_header:has(span:contains("pig"))) .o_kanban_record:has(span:contains("Pigs"))',
        extra_trigger: '.o_kanban_group:has(.o_kanban_header:has(span:contains("goat"))):not(:has(.o_kanban_record))',
        content: 'check that the corkscrew tail filter has taken effect',
        run: () => {},
    }, ...changeFilter("horned tag filter"),
    {
        trigger: '.o_kanban_group:has(.o_kanban_header:has(span:contains("goat"))) .o_kanban_record:has(span:contains("Goats"))',
        extra_trigger: '.o_kanban_group:has(.o_kanban_header:has(span:contains("pig"))):not(:has(.o_kanban_record))',
        content: 'check that the horned filter has taken effect',
        run: () => {},
    }, ...changeFilter("4 Legged tag filter"),
    {
        trigger: '.o_kanban_group:has(.o_kanban_header:has(span:contains("goat"))) .o_kanban_record:has(span:contains("Goats"))',
        extra_trigger: '.o_kanban_group:has(.o_kanban_header:has(span:contains("pig"))) .o_kanban_record:has(span:contains("Pigs"))',
        content: 'check that the 4 legged filter has taken effect',
        run: () => {},
    },
]);
