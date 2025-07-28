import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("im_livechat_session_history_open", {
    steps: () => [
        {
            trigger: "body:has(.o_action_manager)",
            run: "click && press ctrl+k",
        },
        {
            trigger: ".o_command_palette_search input",
            run: "fill /",
        },
        {
            trigger: ".o_command_palette_search input",
            run: "fill Sessions",
        },
        {
            trigger: ".o_command:contains(All Conversations)",
            run: "click",
        },
        {
            trigger: ".o_switch_view[data-tooltip='List']",
            run: "click",
        },
        {
            trigger: ".o_data_cell:contains('test 2')",
            run: "click",
        },
        {
            trigger: ".o-mail-Message-content:contains('Test Channel 2 Msg')",
        },
        {
            trigger: ".oi-chevron-right",
            run: "click",
        },
        {
            trigger: ".o-mail-Message-content:contains('Test Channel 1 Msg')",
        },
    ],
});
