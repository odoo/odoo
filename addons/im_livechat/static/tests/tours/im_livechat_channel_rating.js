import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("im_livechat_channel_rating", {
    steps: () => [
        {
            isActive: ["enterprise"],
            content: "open command palette",
            trigger: ".o_home_menu",
            run: "click && press ctrl+k",
        },
        {
            isActive: ["community"],
            content: "open command palette",
            trigger: "body:has(.o_action_manager)",
            run: "press ctrl+k",
        },
        {
            trigger: ".o_command_palette_search input",
            run: "fill /",
        },
        {
            trigger: ".o_command_palette_search input",
            run: "fill Channels",
        },
        {
            trigger: ".o_command:contains(Live Chat / Channels)",
            run: "click",
        },
        {
            trigger: ".o_kanban_record:contains('Support Session') a",
            run: "click",
        },
        {
            trigger: ".o_kanban_record:contains('Livechat Agent')",
            run: "click",
        },
        {
            trigger: ".modal .o_error_dialog:contains('Access Error')",
        },
    ],
});
