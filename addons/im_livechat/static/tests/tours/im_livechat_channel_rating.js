import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("livechat_operator_cannot_access_other_operator_session", {
    steps: () => [
        {
            trigger: ".o_kanban_record:contains('The channel') a",
            run: "click",
        },
        {
            trigger: ".o_kanban_record:contains('Michel')",
            run: "click",
        },
        {
            trigger: ".modal .o_error_dialog:contains('Access Error')",
        },
    ],
});
