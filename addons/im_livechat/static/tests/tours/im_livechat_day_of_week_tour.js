import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("day_of_week_ordering_tour", {
    steps: () => [
        {
            trigger: ".o_searchview_dropdown_toggler",
            run: "click",
        },
        {
            content: "Select 'Day of the week'",
            trigger: ".o-dropdown-item.o_menu_item:contains('Day of Week')",
            run: "click",
        },
        {
            trigger: ".o_searchview_dropdown_toggler.o-dropdown-caret",
            run: "click",
        },
        {
            trigger: "tbody tr:nth-child(2) th:contains('Saturday')",
        },
        {
            trigger: "tbody tr:nth-child(3) th:contains('Sunday')",
        },
        {
            trigger: "tbody tr:nth-child(4) th:contains('Monday')",
        },
        {
            trigger: "tbody tr:nth-child(5) th:contains('Tuesday')",
        },
        {
            trigger: "tbody tr:nth-child(6) th:contains('Wednesday')",
        },
        {
            trigger: "tbody tr:nth-child(7) th:contains('Thursday')",
        },
        {
            trigger: "tbody tr:nth-child(8) th:contains('Friday')",
        },
    ],
});
