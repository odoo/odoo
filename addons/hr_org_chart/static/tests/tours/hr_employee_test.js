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
            trigger: ".o_org_chart_popup a.o_employee_sub_redirect[data-type='indirect']",
            run: "click",
        },
    ],
});
registry.category("web_tour.tours").add("employee_view_access_multicompany", {
    steps: () => [
        {
            content: "Employee list view",
            trigger: ".o_switch_view.o_list",
            run: "click",
        },
        {
            content: "Click on the employee C",
            trigger: 'table.o_list_table tbody td:contains("Employee C")',
            run: "click",
        },
        {
            content: "Click the number next to employee C",
            trigger: "div[name='child_ids'] .o_org_chart_entry button > .badge:contains('1')",
            run: "click",
        },
    ],
});

