/* @odoo-module */

import { registry } from "@web/core/registry";

const setPager = value => [
    {
        content: "Click Pager",
        trigger: ".o_pager_value:first()",
    },
    {
        content: "Change pager to display lines " + value,
        trigger: "input.o_pager_value",
        run: "text " + value,
    },
    {
        trigger: `.o_pager_value:contains('${value}')`,
        isCheck: true,
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
    test: true,
    steps: () => [
        {
            content: "Open the debug menu",
            trigger: ".o_debug_manager button",
        },
        {
            content: "Click the Set Defaults menu",
            trigger: ".o_debug_manager .dropdown-item:contains(Open View)",
        },
        {
            trigger: ".o_searchview_input",
            run: "text Test Activity View"
        },
        {
            trigger: ".o_menu_item.focus",
            content: "Validate search",
        },
        {
            content: "Select Test Activity View",
            trigger: `.o_data_row td:contains("Test Activity View")`,
        },
        checkRows(["Task 1", "Task 2", "Task 3"]),
        ...setPager("1-2"),
        checkRows(["Task 2", "Task 3"]),
        ...setPager("3"),
        checkRows(["Task 1"]),
    ],
})
