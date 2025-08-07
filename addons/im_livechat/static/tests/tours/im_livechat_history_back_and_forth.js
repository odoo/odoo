import { delay } from "@odoo/hoot-dom";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("im_livechat_history_back_and_forth_tour", {
    steps: () => [
        {
            trigger: "button.o_switch_view.o_list",
            run: "click",
        },
        {
            trigger: ".o_data_cell:contains(Visitor)",
            run: "click",
        },
        {
            trigger: ".o-mail-DiscussContent-threadName[title='Visitor']",
            async run() {
                await delay(1000);
                history.back();
            },
        },
        {
            trigger: ".o_data_cell:contains(Visitor)",
            async run() {
                await delay(0);
                history.forward();
            },
        },
        {
            trigger: ".o-mail-DiscussContent-threadName[title='Visitor']",
            async run() {
                await delay(1000);
                history.back();
            },
        },
        {
            trigger: ".o_data_cell:contains(Visitor)",
        },
    ],
});
