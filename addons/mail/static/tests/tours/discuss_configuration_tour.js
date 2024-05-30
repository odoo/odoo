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
            trigger: ".o-mail-DiscussNotificationSettings label:contains('Mute')",
            content: _t("Click to mute the notifications"),
            run: "click",
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
    ],
});
