import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("im_livechat_history_back_and_forth_tour", {
    test: true,
    steps: () => [
        {
            trigger: "body",
            run: "press ctrl+k"
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
            trigger: ".o_data_cell:contains(Visitor operator)",
        },
        {
            trigger: ".o-mail-DiscussSidebar-item:contains(Visitor).o-active",
            run() {
                history.back();
            },
        },
        {
            trigger: ".o_data_cell:contains(Visitor operator)",
            run() {
                history.forward();
            },
        },
        {
            trigger: ".o-mail-DiscussSidebar-item:contains(Visitor).o-active",
        },
        {
            trigger: ".o-mail-DiscussSidebar-item:contains(Visitor).o-active",
            run() {
                history.back();
            },
        },
        {
            trigger: ".o_data_cell:contains(Visitor operator)",
            run() {},
            isCheck: true,
        },
    ],
});
