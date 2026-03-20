import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

const websiteName = "Website Test Settings";

registry.category("web_tour.tours").add("website_settings_m2o_dirty", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "open settings",
            trigger: ".o_app[data-menu-xmlid='base.menu_administration']",
            run: "click",
        },
        {
            content: "open website settings",
            trigger: ".settings_tab .tab[data-key='website']",
            run: "click",
        },
        {
            content: "check that the 'Shared Customers Accounts' setting is checked",
            trigger: "input[id^='shared_user_account']:checked",
        },
        {
            content: "open website switcher",
            trigger: "input[id^='website_id']",
            run: `edit ${websiteName}`,
        },
        {
            content: `select ${websiteName} in the website switcher`,
            trigger: `li:has(.dropdown-item:contains('${websiteName}'))`,
            run: "click",
        },
        {
            content: `check that the settings of ${websiteName} are loaded (Shared Customers Accounts)`,
            trigger: "input[id^='shared_user_account']:not(:checked)",
        },
    ],
});
