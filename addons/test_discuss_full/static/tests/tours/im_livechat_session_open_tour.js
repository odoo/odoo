import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("im_livechat_session_open", {
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
            trigger: ".o-mail-Thread:contains('The conversation is empty.')",
        },
    ],
});
