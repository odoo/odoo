/** @odoo-module */

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

const websiteName = "Website Test Settings";

registry.category("web_tour.tours").add("website_settings_m2o_dirty", {
    test: true,
    url: "/web",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "open settings",
            trigger: ".o_app[data-menu-xmlid='base.menu_administration']",
        },
        {
            content: "open website settings",
            trigger: ".settings_tab .tab[data-key='website']",
        },
        {
            content: "check that the 'Shared Customers Accounts' setting is checked",
            trigger: "input[id^='shared_user_account']:checked",
            isCheck: true,
        },
        {
            content: "open website switcher",
            trigger: "input[id^='website_id']",
        },
        {
            content: `select ${websiteName} in the website switcher`,
            trigger: `li:has(.dropdown-item:contains('${websiteName}'))`,
        },
        {
            content: `check that the settings of ${websiteName} are loaded (Shared Customers Accounts)`,
            trigger: "input[id^='shared_user_account']:not(:checked)",
            isCheck: true,
        },
        {
            content: "click on the fake website setting after checking the edited website",
            trigger: "button[name='action_website_test_setting']",
        },
        {
            content: "check that we are on '/'",
            trigger: "iframe body div#wrap",
            run: function () {
                if (window.location.pathname !== "/") {
                    // If this fails, it's probably because the change of website
                    // in the settings dirty the record and so there is a dialog
                    // save/discard displayed. This test ensure that does not happen
                    // because it makes actions unreachable in multi website.
                    console.error("We should be on '/' the settings didn't work");
                }
            },
        },
    ],
});
