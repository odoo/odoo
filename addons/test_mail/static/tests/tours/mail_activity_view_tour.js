import { registry } from "@web/core/registry";

const checkRows = (values) => [
    {
        content: `There should be ${values.length} activities`,
        trigger: `.o_activity_view tbody:has(.o_activity_record:count(${values.length}))`,
    },
    ...values.map((value, i) => ({
        content: `Record match ${value}`,
        trigger: `.o_activity_view tbody .o_data_row .o_activity_record:eq(${i}):text(${value})`,
    })),
];

registry.category("web_tour.tours").add("mail_activity_view_tour", {
    steps: () => [
        {
            content: "Open the debug menu",
            trigger: ".o_debug_manager button",
            run: "click",
        },
        {
            content: "Click the Set Defaults menu",
            trigger: ".o-dropdown-item:contains(Open View)",
            run: "click",
        },
        {
            trigger: ".o_searchview_input",
            run: "edit Test Activity View",
        },
        {
            trigger: ".o_searchview_autocomplete .o-dropdown-item.focus",
            content: "Validate search",
            run: "click",
        },
        {
            content: "Select Test Activity View",
            trigger: `.o_data_row td:contains("Test Activity View")`,
            run: "click",
        },
        ...checkRows(["Task 1", "Task 2", "Task 3"]),
        {
            content: "Click Pager",
            trigger: "span.o_pager_value",
            run: "click",
        },
        {
            content: "Change pager to display lines 1-2",
            trigger: "input.o_pager_value",
            run: `edit 1-2`,
        },
        {
            trigger: ".o_activity_view_table",
            run: "click",
        },
        {
            trigger: `span.o_pager_value:contains(1-2)`,
        },
        ...checkRows(["Task 2", "Task 3"]),
        {
            trigger: ".o_pager_next",
            run: "click",
        },
        {
            trigger: `span.o_pager_value:contains(3-3)`,
        },
        ...checkRows(["Task 1"]),
    ],
});
