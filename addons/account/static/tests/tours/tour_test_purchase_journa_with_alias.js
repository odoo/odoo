import { accountTourSteps } from "@account/js/tours/account";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('test_accounting_dashboard_purchase_journal_with_alias', {
    url: "/odoo",
    steps: () => [
    ...accountTourSteps.goToAccountMenu("Go to Invoicing"),
    {
        content: "Ensure the correct text is displayed",
        trigger: ".o_kanban_record:contains('Test Alias') .bill_guide_right:contains('Send a bill to'):contains('purchase-company_1_data@test.com')",
    },
]});
