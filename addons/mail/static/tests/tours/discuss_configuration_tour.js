import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("discuss_configuration_tour", {
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="mail.menu_root_discuss"]',
            run: "click",
        },
        {
            trigger: ".o_main_navbar button:text('Configuration')",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('User Settings')",
        },
        {
            trigger: ".dropdown-menu .dropdown-item:text('Notifications')",
            run: "click",
        },
        {
            trigger: "button:text('All Messages')",
            run: "click",
        },
        {
            trigger: "button:text('Mentions Only')",
            run: "click",
        },
        {
            trigger: "button:text('Nothing')",
            run: "click",
        },
        {
            trigger: ".modal-header button[aria-label='Close']",
            run: "click",
        },
        {
            trigger: ".o_main_navbar button:text('Configuration')",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('User Settings')",
        },
        {
            trigger: ".dropdown-menu .dropdown-item:text('Voice & Video')",
            run: "click",
        },
        {
            trigger: ".o-mail-DeviceSelect-button[data-kind='audioinput']",
        },
        {
            trigger: "input[title='Voice detection sensitivity']",
        },
        {
            trigger: "label[aria-label='Enable Push-to-talk']",
            run: "click",
        },
        {
            trigger: "span:text('Click the button below to register a new shortcut.')",
        },
        {
            trigger: "input[title='Delay after releasing push-to-talk']",
        },
        {
            trigger: "button[title='Video']",
            run: "click",
        },
        {
            trigger: "input[aria-label='Blur video background']",
            run: "click",
        },
        {
            trigger: "div[title='Background blur intensity'] span:has(:text('Intensity'))",
        },
        {
            trigger: "div[title='Edge blur intensity'] span:has(:text('Edge Softness'))",
        },
        {
            trigger: ".modal-header button[aria-label='Close']",
            run: "click",
        },
        {
            trigger: ".o_main_navbar button:text('Configuration')",
            run: "click",
        },
        {
            trigger: ".dropdown-menu a:text('Settings')",
            expectUnloadPage: true,
            run: "click",
        },
        {
            trigger: "#discuss_setting",
        },
    ],
});
