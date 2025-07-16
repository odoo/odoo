import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("im_livechat_report_pivot_redirect_tour", {
    steps: () => [
        {
            content: "Click on a cell with a single related record",
            trigger: `.o_pivot table tbody tr:has(th:contains(operator_1)) td:eq(0)`,
            run: "click",
        },
        { trigger: ".o-mail-Discuss" },
        {
            content: "go back to the pivot view.",
            trigger: ".o_back_button",
            run: "click",
        },
        {
            content: "Click on a cell with multiple related records",
            trigger: `.o_pivot table tbody tr:has(th:contains(operator_2)) td:eq(0)`,
            run: "click",
        },
        { trigger: ".o_list_view" },
    ],
});
