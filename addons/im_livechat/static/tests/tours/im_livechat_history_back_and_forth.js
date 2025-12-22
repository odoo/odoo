import { registry } from "@web/core/registry";
import { delay } from "@web/core/utils/concurrency";

registry.category("web_tour.tours").add("im_livechat_history_back_and_forth_tour", {
    steps: () => [
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
            async run() {
                await delay(0);
                history.back();
            },
        },
        {
            trigger: ".o_data_cell:contains(Visitor operator)",
            async run() {
                await delay(0);
                history.forward();
            },
        },
        {
            trigger: ".o-mail-DiscussSidebar-item:contains(Visitor).o-active",
            async run(helpers) {
                await delay(0);
                await helpers.click();
            },
        },
        {
            trigger: ".o-mail-DiscussSidebar-item:contains(Visitor).o-active",
            async run() {
                await delay(0);
                history.back();
            },
        },
        {
            trigger: ".o_data_cell:contains(Visitor operator)",
        },
    ],
});
