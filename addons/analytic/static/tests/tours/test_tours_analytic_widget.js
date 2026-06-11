import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";
import { accountTourSteps } from "@account/js/tours/account";

registry.category("web_tour.tours").add("analytic_distribution_widget", {
    url: "/odoo",
    steps: () => {
        const urlParams = new URLSearchParams(window.location.search);
        const plan1Col = urlParams.get('plan_1_col');
        if (plan1Col) {
            window.sessionStorage.setItem('plan_1_col', plan1Col); // saved in the session storage as stepping into other pages removes url params
        }
        return [
            stepUtils.showAppsMenuItem(),
            ...accountTourSteps.goToAccountMenu("Open the accounting module"),
            {
                content: "Open Accounting dropdown menu where Analytic Items can be found",
                trigger: '.o-dropdown[data-menu-xmlid="account.menu_finance_entries"]',
                run: "click",
            },
            {
                content: "Open Analytic Items",
                trigger: '.o-dropdown-item[data-menu-xmlid="account.menu_action_analytic_lines_tree"]',
                run: "click",
            },
            {
                content: "Opening optional column dropdown",
                trigger: ".o_optional_columns_dropdown_toggle",
                run: "click",
            },
            {
                content: "Adding the analytic distribution column",
                trigger: ".o-dropdown-item:contains('Analytic Distribution') input",
                run: "click",
            },
            {
                content: "Select first analytic item line",
                trigger: ".o_data_row:nth-child(1) input",
                run: "click",
            },
            {
                content: "Select second analytic item line",
                trigger: ".o_data_row:nth-child(2) input",
                run: "click",
            },
            {
                content: "Click on the analytic distribution tags of the first line to open the widget",
                trigger: ".o_data_row:nth-child(1) .o_tag:nth-child(1) > .o_tag_badge_text",
                run: "click",
            },
            {
                content: "Click update for the first column plan",
                trigger: ".o_list_table th:contains('Plan 1') > a",
                run: "click",
            },
            {
                content: "Click to trigger the dropdown for the accounts available for this plan",
                trigger: `input#${window.sessionStorage.getItem('plan_1_col')}`,
                run: "click",
            },
            {
                content: "Choose the other account available for this plan",
                trigger: ".o-autocomplete--dropdown-item:contains('Other Account') > a",
                run: "click",
            },
            {
                content: "Click away from the window to confirm changes",
                trigger: ".o_list_renderer",
                run: "click",
            },
            {
                content: "Click on update for the multi line edit",
                trigger: ".o_technical_modal button:nth-child(1)",
                run: "click",
            },
            {
                content: "Check that analytic distribution values are updated correctly for Analytic Item 2",
                trigger: ".o_data_row:nth-child(1) .o_field_analytic_distribution:has(.o_tag_badge_text:contains('Other Account'))",
            },
            {
                content: "Check that analytic distribution values are updated correctly for Analytic Item 2",
                trigger: ".o_data_row:nth-child(1) .o_field_analytic_distribution:has(.o_tag_badge_text:contains('Account 4'))",
            },
            {
                content: "Check that analytic distribution values are updated correctly for Analytic Item 1",
                trigger: ".o_data_row:nth-child(2) .o_field_analytic_distribution:has(.o_tag_badge_text:contains('Other Account'))",
            },
            {
                content: "Check that analytic distribution values are updated correctly for Analytic Item 1",
                trigger: ".o_data_row:nth-child(2) .o_field_analytic_distribution:has(.o_tag_badge_text:contains('Account 3'))",
            },
        ];
    }
});
