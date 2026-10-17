import { registry } from "@web/core/registry";

const row = ".o_data_row:contains(Edit URL Page)";
const urlCell = `${row} .o_data_cell[name=url]`;

// Edits the URL of the selected page (checking its current value first) and
// answers the confirmation dialog.
const editUrl = (currentUrl, newUrl, answer) => [
    {
        content: `Click on the URL ${currentUrl}`,
        trigger: `${urlCell}:contains(${currentUrl})`,
        run: "click",
    },
    {
        content: `Change the URL to ${newUrl}`,
        trigger: ".o_selected_row .o_data_cell[name=url] input",
        run: `edit ${newUrl} && press Enter`,
    },
    {
        content: `Click on '${answer}' in the confirmation dialog`,
        trigger: `.modal:contains(Some links pointing to these old URLs) .modal-footer button:contains(${answer})`,
        run: "click",
    },
];

registry.category("web_tour.tours").add("website_page_manager_edit_url", {
    steps: () => [
        {
            content: "Select the page",
            trigger: `${row} .o_list_record_selector input`,
            run: "click",
        },
        ...editUrl("/edit-url-page", "/edit-url-cancelled", "Cancel"),
        // Starting from "/edit-url-page" again checks that the cancel kept it.
        ...editUrl("/edit-url-page", "/edit-url-updated", "Update"),
        {
            content: "Check that the URL has been updated and unselect the page",
            trigger: `${row}:has(.o_data_cell[name=url]:contains(/edit-url-updated)) .o_list_record_selector input`,
            run: "click",
        },
        {
            content: "Open the page",
            trigger: `${row}:not(.o_data_row_selected) .o_data_cell[name=url]`,
            run: "click",
        },
        {
            content: "Check that the page is opened at its new URL, then go to the old URL",
            trigger: ":iframe #wrap:contains(Edit URL Page content)",
            run: "goToUrl /edit-url-page",
            expectUnloadPage: true,
        },
        {
            content: "Check that the old URL leads to a 404 page",
            trigger: "#wrap h2:contains(find the page you)",
        },
    ],
});
