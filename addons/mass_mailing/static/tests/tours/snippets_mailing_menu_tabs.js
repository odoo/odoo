import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

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
        trigger: '.o_mailing_template_preview_wrapper [data-name="empty"]',
        run: "click",
    },
    {
        content: "Click on the 'Design' tab.",
        trigger: 'button[data-name="theme"]',
        run: "click",
    },
    {
        content: "Verify that the customize panel is not empty.",
        trigger: ".o_design_tab:not(:empty)",
    },
    {
        content: "Click on the style tab.",
        trigger: 'button[data-name="customize"]',
        run: "click",
    },
    {
        content: "Click on the 'Design' tab.",
        trigger: 'button[data-name="theme"]',
        run: "click",
    },
    {
        content: "Verify that the customize panel is not empty.",
        trigger: ".tab-content .o_design_tab:not(:empty)",
    },
    ...stepUtils.discardForm(),
]});
