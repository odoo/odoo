/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('snippets_mailing_menu_tabs', {
    url: '/odoo',
    steps: () => [
    stepUtils.showAppsMenuItem(), {
        content: "Select the 'Email Marketing' app.",
        trigger: '.o_app[data-menu-xmlid="mass_mailing.mass_mailing_menu_root"]',
        run: "click",
    },
    {
        content: "Click on the create button to create a new mailing.",
        trigger: 'button.o_list_button_add',
        run: "click",
    },
    {
        content: "Click on the 'Start From Scratch' template.",
        trigger: ':iframe #empty',
        run: "click",
    },
    {
        content: "Click on the 'Design' tab.",
        trigger: '.o_we_customize_design_btn',
        run: "click",
    },
    {
        content: "Click on the empty 'DRAG BUILDING BLOCKS HERE' area.",
        trigger: ':iframe .oe_structure.o_mail_no_options',
        run: "click",
    },
    {
        content: "Click on the 'Design' tab.",
        trigger: '.o_we_customize_design_btn',
        run: "click",
    },
    {
        content: "Verify that the customize panel is not empty.",
        trigger: '.o_we_customize_panel .snippet-option-DesignTab',
    },
    {
        content: "Click on the style tab.",
        trigger: '.o_we_customize_snippet_btn',
        run: "click",
    },
    {
        content: "Click on the 'Design' tab.",
        trigger: '.o_we_customize_design_btn',
        run: "click",
    },
    {
        content: "Verify that the customize panel is not empty.",
        trigger: '.o_we_customize_panel .snippet-option-DesignTab',
    },
    ...stepUtils.discardForm(),
]});
