import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("create_channel_from_command_palette_tour", {
    steps: () => [
        {
            trigger: ".o_main_navbar",
            run: "press ctrl+k",
        },
        {
            trigger: ".o_command_palette_search input",
            run: `fill @Test_channel_${Date.now()}`,
        },
        {
            trigger: ".o-mail-DiscussCommand-createChannel",
            run: "click",
        },
        {
            trigger: ".o-mail-CreateChannelDialog input",
            run: "press Enter",
        },
        {
            trigger: ".o-mail-ChatWindow",
        },
    ],
});
