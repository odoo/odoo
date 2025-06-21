import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("im_livechat_report_pivot_redirect_tour", {
    steps: () => [
        {
            content: "open command palette",
            trigger: "body",
            run: "press ctrl+k",
        },
        {
            trigger: ".o_command_palette_search input",
            run: "fill /",
        },
        {
            trigger: ".o_command_palette_search input",
            run: "fill Reporting",
        },
        {
            trigger: ".o_command:contains(Agents)",
            run: "click",
        },
        {
            content: "click on a cell that has a single related record.",
            trigger: ".o_pivot .o_pivot_cell_value:contains(1)",
            run: "click",
        },
        {
            trigger: ".o-mail-Discuss",
        },
    ],
});
