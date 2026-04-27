/** @odoo-module **/

    import { _t } from "@web/core/l10n/translation";
    import { registry } from "@web/core/registry";
    import { stepUtils } from "@web_tour/tour_service/tour_utils";
    import { markup } from "@odoo/owl";

    registry.category("web_tour.tours").add('hr_expense_extract_tour' , {
        url: "/odoo",
        steps: () => [stepUtils.showAppsMenuItem(), {
        trigger: '.o_app[data-menu-xmlid="hr_expense.menu_hr_expense_root"]',
        content: markup(_t("<b>Wasting time recording your receipts?</b> Let’s try a better way.")),
        tooltipPosition: 'bottom',
        run: "click",
    }, {
        trigger: '.o_nocontent_help a.btn-primary',
        content: _t("Try the AI with a sample receipt."),
        tooltipPosition: 'bottom',
        run: "click",
    }, {
        trigger: ".o_expense_flex",
        content: _t("Choose a receipt."),
        tooltipPosition: 'top',
        run: "click",
    }, {
        trigger: "button[name='action_submit_expenses']",
        content: _t("Report this expense to your manager for validation."),
        tooltipPosition: 'bottom',
        run: "click",
    }, {
        trigger: '.dropdown-toggle[data-menu-xmlid="hr_expense.menu_hr_expense_report"]',
        content: _t("Your manager will have to approve (or refuse) your expense reports."),
        tooltipPosition: 'bottom',
        run: "click",
    }, {
        trigger: '.dropdown-item[data-menu-xmlid="hr_expense.menu_hr_expense_sheet_all_to_approve"]',
        content: _t("Your manager will have to approve (or refuse) your expense reports."),
        tooltipPosition: 'bottom',
        run: "click",
    }]});
