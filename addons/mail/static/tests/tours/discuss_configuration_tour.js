import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("discuss_configuration_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="mail.menu_root_discuss"]',
            run: "click",
        },
        {
            trigger: ".o_main_navbar button:contains('Configuration')",
            run: "click",
        },
        {
            trigger: ".dropdown-menu a:contains('Notification')",
            run: "click",
        },
        {
            trigger: "button:contains('All Messages')",
            run: "click",
        },
        {
            trigger: "button:contains('Mentions Only')",
            run: "click",
        },
        {
            trigger: "button:contains('Nothing')",
            run: "click",
        },
        {
            trigger: ".modal-header button[aria-label='Close']",
            run: "click",
        },
        {
            trigger: ".o_main_navbar button:contains('Configuration')",
            run: "click",
        },
        {
            trigger: ".dropdown-menu a:contains('Voice & Video')",
            run: "click",
        },
        {
            trigger: "select[name='inputDevice']",
        },
        {
            trigger: "button:contains('Voice Detection')",
            run: "click",
        },
        {
            trigger: "span:contains('Voice detection sensitivity')",
        },
        {
            trigger: "button:contains('Push to Talk')",
            run: "click",
        },
        {
            trigger: "label:contains('Push-to-talk key')",
        },
        {
            trigger: "label:contains('Delay after releasing push-to-talk')",
        },
        {
            trigger: "input[aria-label='Show video participants only']",
        },
        {
            trigger: "input[aria-label='Blur video background']",
            run: "click",
        },
        {
            trigger: "label:contains('Background blur intensity')",
        },
        {
            trigger: "label:contains('Edge blur intensity')",
        },
    ],
});
