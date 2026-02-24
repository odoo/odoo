import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("indirect_subordinates_tour", {
    steps: () => [
        {
            content: "Click the number next to employee georges",
            trigger: "div[name='child_ids'] .o_org_chart_entry button > .badge:contains('2')",
            run: "click",
        },
        {
            content: "Click Indirect Subordinates",
            trigger: ".o_org_chart_popup button.o_employee_sub_redirect[data-type='indirect']",
            run: "click",
        },
    ],
});
