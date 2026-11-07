import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("fleet_manager_tour", {
    steps: () => [
        {
            content: "search a fleet manager for a vehicle of company A",
            trigger: ".o_field_widget[name=manager_id] input",
            run: "edit Fleet Officer",
        },
        {
            content: "the officer allowed in company A is proposed",
            trigger: ".o_field_widget[name=manager_id] .o-autocomplete--dropdown-menu li:contains(Fleet Officer Allowed)",
        },
        {
            content: "the officer allowed in company B only is not proposed",
            trigger: ".o_field_widget[name=manager_id] .o-autocomplete--dropdown-menu:not(:has(li:contains(Fleet Officer Foreign)))",
        },
    ],
});
