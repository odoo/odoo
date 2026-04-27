/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('planning_avatar_card_non_hr_user', {
    url: '/odoo?debug=tests',
    steps: () => [{
    trigger: '.o_app[data-menu-xmlid="planning.planning_menu_root"]',
    content: "Open the Planning app",
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: 'input[type="range"]',
    content: "The initial default scale should be week",
    run() {
        const subjectValue = document.querySelector('input[type="range"]').value;
        if (subjectValue !== "2") {
            console.error(
                `Default scale should be week (2) (actual: ${subjectValue})`
            );
        }
    },
},{
    trigger: ".o_searchview_dropdown_toggler",
    content: "Open Filter",
    run: "click",
}, {
    trigger: ".o_add_custom_filter",
    content: "Click on custom filter",
    run: "click",
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
    run: "click",
}, {
    trigger: ".o_searchview_input",
    content: "Search planning shifts assigned to 3D Printer Room",
    run: "edit 3D Printer Room",
}, {
    trigger: ".o_menu_item.dropdown-item > a:not(.o_expand)",
    content: "Select filter resource = 3D Printer Room",
    run: 'click',
}, {
    trigger: '.o_gantt_row_header .o_avatar.o_field_many2one_avatar > span:contains("3D Printer Room")',
    content: 'Wait for the resource "3D Printer Room" to be displayed',
    run: "click",
}, {
    trigger: ".o_gantt_row_header .o_avatar .o_material_resource > i.fa-wrench",
    content: 'Click on the icon of the material resource "3D Printer Room"',
    run: 'click',
}, {
    trigger: ".o_avatar_card .o_resource_roles_tags .o_tag",
    content: "Wait for the avatar card with roles in it to appear, it should not display a default role as the user has no hr access",
    run: () => {
        const nodes = document.querySelectorAll(".o_avatar_card .o_resource_roles_tags .o_tag");
        if (nodes.length !== 2) {
            console.error('Two roles should be displayed on the avatar card of the resource.');
        }
        const default_role = document.querySelector(".o_avatar_card .o_resource_roles_tags .o_tag > i.fa-star");
        if (default_role) {
            console.error('The default role information should not be displayed as it is not accessible for the current user');
        }
    },
}]});
