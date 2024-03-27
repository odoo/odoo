/* @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("discuss_configuration_tour", {
    test: true,
    url: "/web",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Disucss app",
            trigger: '.o_app[data-menu-xmlid="mail.menu_root_discuss"]',
            run: "click",
        },
        {
            trigger: ".o_main_navbar button:contains('Configuration')",
            content: _t("Click to see the setting options"),
            run: "click",
        },
        {
            trigger: ".dropdown-menu a:contains('Notification')",
            content: _t("Open the Notification settings"),
            run: "click",
        },
        {
            trigger: ".o-mail-DiscussNotificationSettings-item:contains('Mute') input",
            content: _t("Click to mute the notifications"),
            run: "click",
        },
        {
            trigger: "select:contains('Until I turn it back on')",
            content: _t("Open the selection menu"),
        },
        {
            trigger: "button:contains('All Messages')",
            content: _t("Server notification settings"),
        },
        {
            trigger: "button:contains('Mentions Only')",
            content: _t("Server notification settings"),
        },
        {
            trigger: "button:contains('Nothing')",
            content: _t("Server notification settings"),
        },
        {
            trigger: ".modal-header button[aria-label='Close']",
            content: _t("Click to close"),
        },
        {
            trigger: ".o_main_navbar button:contains('Configuration')",
            content: _t("Click to see the setting options"),
            run: "click",
        },
        {
            trigger: ".dropdown-menu a:contains('Voice & Video')",
            content: _t("Open the Voice & Video settings"),
            run: "click",
        },
        {
            trigger: "select[name='inputDevice']",
            content: _t("Select the input device"),
        },
        {
            trigger: "button:contains('Voice Detection')",
            content: _t("Click to enable voice detection"),
            run: "click",
        },
        {
            trigger: "label:contains('Voice detection threshold')",
            content: _t("Adjust the voice detection threshold"),
        },
        {
            trigger: "button:contains('Push to Talk')",
            content: _t("Click to enable push to talk"),
            run: "click",
        },
        {
            trigger: "label:contains('Push-to-talk key')",
            content: _t("Click to register a new key"),
        },
        {
            trigger: "label:contains('Delay after releasing push-to-talk')",
            content: _t("Adjust the delay after releasing push-to-talk"),
        },
        {
            trigger: "input[aria-label='Show video participants only']",
            content: _t("Click to show only video participants"),
        },
        {
            trigger: "input[aria-label='Blur video background']",
            content: _t("Click to blur the video background"),
            run: "click",
        },
        {
            trigger: "label:contains('Background blur intensity')",
            content: _t("Adjust the background blur intensity"),
        },
        {
            trigger: "label:contains('Edge blur intensity')",
            content: _t("Adjust the edge blur intensity"),
            isCheck: true,
        },
    ],
});
