import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_cloc_user_space", {
    steps: () => [
        {
            trigger: ".o_debug_manager button",
            run: "click",
        },
        {
            trigger: ".o-overlay-container .o-dropdown-item:contains(Count LoC)",
            run: "click",
        },
        {
            trigger: ".modal:contains(Count lines of code)",
        },
        {
            trigger: "tr:has(td:contains(/^ir.actions.server$/)):contains(test cloc user space)",
        },
    ],
});
