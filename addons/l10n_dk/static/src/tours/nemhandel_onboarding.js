import { registry } from "@web/core/registry";
import { accountTourSteps } from "@account/js/tours/account";

registry.category("web_tour.tours").add("nemhandel_onboarding_tour", {
    url: "/odoo",
    steps: () => [
        ...accountTourSteps.goToAccountMenu("Let’s register on Nemhandel."),
        {
            content: "Configuration",
            trigger: "button[data-menu-xmlid='account.menu_finance_configuration']",
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            content: "Settings",
            trigger: "a[data-menu-xmlid='account.menu_account_config']",
            tooltipPosition: "right",
            run: "click",
        },
        {
            content: "Click to start signing up",
            trigger: "button[name='action_open_nemhandel_form']",
            run: "click",
        },
    ],
});
