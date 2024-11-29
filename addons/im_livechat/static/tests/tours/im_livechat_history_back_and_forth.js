import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("im_livechat_history_back_and_forth_tour", {
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
            trigger: "button.o_switch_view.o_list",
            run: "click",
        },
        {
            trigger: ".o_data_cell:contains(Visitor operator)",
            run: "click",
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
            run: "click",
        },
        {
            trigger: ".o-mail-DiscussSidebar-item:contains(Visitor).o-active",
            run() {
                history.back();
            },
        },
        {
            trigger: ".o_data_cell:contains(Visitor operator)",
        },
    ],
});
