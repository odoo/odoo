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
            run: "click",
        },
        {
            trigger: ".o_switch_view[data-tooltip='List']",
            run: "click",
        },
        {
            trigger: ".d-block:contains('Participants')",
            run: "click",
        },
        {
            trigger: ".o_data_cell:contains('test 1')",
            run: "click",
        },
        {
            trigger: ".o-mail-Message-content:contains('Test Channel 1 Msg')",
        },
        {
            trigger: ".oi-chevron-right",
            run: "click",
        },
        {
            trigger: ".o-mail-Message-content:contains('Test Channel 2 Msg')",
        },
    ],
});
