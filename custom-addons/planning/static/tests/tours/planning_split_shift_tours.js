/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('planning_split_shift_week', {
    url: '/web?debug=tests',
    test: true,
    steps: () => [{
    trigger: '.o_app[data-menu-xmlid="planning.planning_menu_root"]',
    content: "Let's start managing your employees' schedule!",
    position: 'bottom',
}, {
    trigger: ".scale_button_selection",
    content: "The initial default scale should be week",
    run() {
        const subjectValue = document.querySelector('.scale_button_selection').textContent;
        if (subjectValue !== "Week") {
            console.error(
                `Default scale should be week (actual: ${subjectValue})`
            );
        }
    },
},{
    trigger: ".o_searchview_dropdown_toggler",
    content: "Open Filter",
}, {
    trigger: ".o_add_custom_filter",
    content: "Click on custom filter",
}, {
    trigger: ".o_model_field_selector",
    content: "Write domain excluding open shifts",
    run() {
        const input = document.querySelector(".o_domain_selector_debug_container textarea")
        input.value = '[("resource_id", "!=", False)]';
        input.dispatchEvent(new Event("change", { bubbles: true, cancelable: false }));
    }
}, {
    trigger: ".modal-footer > .btn-primary",
    content: "Add custom filter",
}, {
    trigger: ".o_searchview_input",
    content: "Search planning shifts assigned to Aramis",
    run: "text Aramis",
}, {
    trigger: ".o_menu_item.dropdown-item > a:not(.o_expand)",
    content: "Select filter resource = Aramis",
    run: 'click',
}, {
    trigger: ".o_searchview_input",
    content: "Search planning shifts assigned to Athos",
    run: "text Athos",
}, {
    trigger: ".o_menu_item.dropdown-item > a:not(.o_expand)",
    content: "Select filter resource = Athos",
    run: 'click',
}, {
    trigger: ".o_searchview_input",
    content: "Search planning shifts assigned to Porthos",
    run: "text Porthos",
}, {
    trigger: ".o_menu_item.dropdown-item > a:not(.o_expand)",
    content: "Select filter resource = Porthos",
    run: 'click',
}, {
    trigger: ".o_gantt_pill_split_tool[data-split-tool-pill-id='__pill__1_0']",
    content: "Split the slot assigned to Aramis after one day",
    run: 'click',
}, {
    trigger: ".o_gantt_pill_wrapper[data-pill-id='__pill__4']",
    content: "Wait for the new shift to appear",
    run() {},
}, {
    trigger: ".o_gantt_pill_split_tool[data-split-tool-pill-id='__pill__3_1']",
    content: "Split the slot assigned to Athos after two days",
    run: 'click',
}, {
    trigger: ".o_gantt_pill_wrapper[data-pill-id='__pill__5']",
    content: "Wait for the new shift to appear",
    run() {},
}, {
    trigger: ".o_gantt_pill_split_tool[data-split-tool-pill-id='__pill__3_0']",
    content: "Split the first slot assigned to Athos after one day",
    run: 'click',
}, {
    trigger: ".o_gantt_pill_wrapper[data-pill-id='__pill__6']",
    content: "Wait for the new shift to appear",
    run() {},
}, {
    trigger: ".o_gantt_pill_split_tool[data-split-tool-pill-id='__pill__6_0']",
    content: "Split the first slot assigned to Porthos after one day",
    run: 'click',
}]});
