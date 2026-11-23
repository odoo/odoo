/** @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("im_livechat_history_back_and_forth_tour", {
    test: true,
    steps: () => [
        {
            trigger: "body",
            // Open Command Palette
            run() {
                this.$anchor[0].dispatchEvent(
                    new KeyboardEvent("keydown", { key: "K", ctrlKey: true, bubbles: true })
                );
            },
        },
        {
            trigger: ".o_command_palette_search input",
            run: "text /",
        },
        {
            trigger: ".o_command_palette_search input",
            run: "text Live Chat",
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
