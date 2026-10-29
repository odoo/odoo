import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("hr_expense_pay_tour", {
    steps: () => [
        {
            content: "Without a receipt, only attaching one is highlighted, and refusing comes after paying",
            trigger: ".o_form_view .o_expense_pay:not(.btn-primary) ~ .o_expense_refuse_manager",
        },
        {
            content: "Pay the approved expense",
            trigger: ".o_form_view .o_expense_pay",
            run: "click",
        },
        {
            content: "The expense is paid and cannot be paid twice",
            trigger: ".o_form_view .o_statusbar_status .o_arrow_button_current:contains(Paid)",
        },
        {
            trigger: ".o_form_view:not(:has(.o_expense_pay))",
        },
    ],
});
