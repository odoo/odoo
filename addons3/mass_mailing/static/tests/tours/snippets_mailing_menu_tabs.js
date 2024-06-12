/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('snippets_mailing_menu_tabs', {
    test: true,
    url: '/web',
    steps: () => [
    stepUtils.showAppsMenuItem(), {
        content: "Select the 'Email Marketing' app.",
        trigger: '.o_app[data-menu-xmlid="mass_mailing.mass_mailing_menu_root"]',
    },
    {
        content: "Click on the create button to create a new mailing.",
        trigger: 'button.o_list_button_add',
    },
    {
        content: "Click on the 'Start From Scratch' template.",
        trigger: 'iframe #empty',
    },
    {
        content: "Click on the 'Design' tab.",
        trigger: 'iframe .o_we_customize_design_btn',
    },
    {
        content: "Click on the empty 'DRAG BUILDING BLOCKS HERE' area.",
        trigger: 'iframe .oe_structure.o_mail_no_options',
    },
    {
        content: "Click on the 'Design' tab.",
        trigger: 'iframe .o_we_customize_design_btn',
    },
    {
        content: "Verify that the customize panel is not empty.",
        trigger: 'iframe .o_we_customize_panel .snippet-option-DesignTab',
        run: () => null, // it's a check
    },
    {
        content: "Click on the style tab.",
        trigger: 'iframe .o_we_customize_snippet_btn',
    },
    {
        content: "Click on the 'Design' tab.",
        trigger: 'iframe .o_we_customize_design_btn',
    },
    {
        content: "Verify that the customize panel is not empty.",
        trigger: 'iframe .o_we_customize_panel .snippet-option-DesignTab',
        run: () => null, // it's a check
    },
    ...stepUtils.discardForm(),
]});
