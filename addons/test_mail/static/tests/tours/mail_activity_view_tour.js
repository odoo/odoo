import { registry } from "@web/core/registry";

const setPager = value => [
    {
        content: "Click Pager",
        trigger: ".o_pager_value:first()",
        run: "click",
    },
    {
        content: "Change pager to display lines " + value,
        trigger: "input.o_pager_value",
        run: `edit ${value} && click body`,
    },
    {
        trigger: `.o_pager_value:contains('${value}')`,
    },
]


const checkRows = values => {
    return {
        trigger: '.o_activity_view',
        run: () => {
            const dataRow = document.querySelectorAll('.o_activity_view tbody .o_data_row .o_activity_record');
            if (dataRow.length !== values.length) {
                throw Error(`There should be ${values.length} activities`);
            }
            values.forEach((value, index) => {
                if (dataRow[index].textContent !== value) {
                    throw Error(`Record does not match ${value} != ${dataRow[index]}`);
                }
            });
        }
    }
}

registry.category("web_tour.tours").add("mail_activity_view", {
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
            run: "edit Test Activity View"
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
        checkRows(["Task 1", "Task 2", "Task 3"]),
        ...setPager("1-2"),
        checkRows(["Task 2", "Task 3"]),
        ...setPager("3"),
        checkRows(["Task 1"]),
    ],
})
