import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("im_livechat_report_pivot_redirect_tour", {
    steps: () => [
        {
            content: "open command palette",
            trigger: "body:has(.o_action_manager)",
            run: "click && press ctrl+k",
        },
        {
            trigger: ".o_command_palette_search input",
            run: "fill /Reporting",
        },
        {
            trigger: ".o_command:contains(Agents)",
            run: "click",
        },
        {
            content: "click on a cell that has a single related record",
            trigger: ".o_pivot table tbody tr:eq(2) td:eq(0)",
            run: "click",
        },
        { trigger: ".o-mail-Discuss" },
        {
            content: "go back to the pivot view.",
            trigger: ".o_back_button",
            run: "click",
        },
        {
            content: "click on a cell that has more than one related record",
            trigger: ".o_pivot table tbody tr:eq(0) td:eq(0)",
            run: "click",
        },
        { trigger: ".o_list_view" },
    ],
});
