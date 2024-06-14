import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("im_livechat_session_history_open", {
    test: true,
    steps: () => [
        {
            trigger: "body",
            run: "press ctrl+k",
        },
        {
            trigger: ".o_command_palette_search input",
            run: "fill /",
        },
        {
            trigger: ".o_command_palette_search input",
            run: "fill Live Chat",
        },
        {
            trigger: ".o_command:contains(Sessions History)",
        },
        {
            trigger: ".o_data_cell:contains(test 1)",
            run: "click",
        },
        {
            trigger: ".o-mail-DiscussSidebar-item:contains(test 2)",
            run: "click",
        },
    ],
});
