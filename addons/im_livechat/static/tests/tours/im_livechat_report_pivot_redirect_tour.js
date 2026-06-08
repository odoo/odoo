import { registry } from "@web/core/registry";

function makePivotRedirectTourSteps(singleRecordName, multiRecordName) {
    return [
        {
            content: "Click on a cell with a single related record",
            trigger: `.o_pivot table tbody tr:has(th:contains(${singleRecordName})) td:eq(0)`,
            run: "click",
        },
        {
            trigger: ".o-mail-Discuss",
            content: "Verify redirection to the single record view",
        },
        {
            content: "Go back to the pivot view",
            trigger: ".o_back_button",
            run: "click",
        },
        {
            content: "Click on a cell with a multiple related records",
            trigger: `.o_pivot table tbody tr:has(th:contains(${multiRecordName})) td:eq(0)`,
            run: "click",
        },
        {
            trigger: ".o_list_view",
            content: "Verify redirection to the list view for multiple records",
        },
    ];
}

registry.category("web_tour.tours").add("im_livechat_agents_report_pivot_redirect_tour", {
    steps: () => makePivotRedirectTourSteps("test 1", "test 2"),
});

registry.category("web_tour.tours").add("im_livechat_sessions_report_pivot_redirect_tour", {
    steps: () => makePivotRedirectTourSteps("operator_1", "operator_2"),
});
