import { registry } from "@web/core/registry";

const pageRow = ".o_data_row:contains(Edit URL Page)";
const pageUrlCell = `${pageRow} .o_data_cell[name=url]`;

// Edits the URL of the selected page, after checking its current value, and
// clicks on the given button of the confirmation dialog.
const editPageUrl = (oldUrl, newUrl, dialogButton) => [
    {
        content: `Click on the URL ${oldUrl}`,
        trigger: `${pageUrlCell}:contains(${oldUrl})`,
        run: "click",
    },
    {
        content: `Change the URL to ${newUrl}`,
        trigger: ".o_selected_row .o_data_cell[name=url] input",
        run: `edit ${newUrl} && press Enter`,
    },
    {
        content: `Click on '${dialogButton}' in the confirmation dialog`,
        trigger: `.modal:contains(Some links pointing to these old URLs) .modal-footer button:contains(${dialogButton})`,
        run: "click",
    },
];

registry.category("web_tour.tours").add("website_page_manager_edit_url", {
    steps: () => [
        {
            content: "Select the page",
            trigger: `${pageRow} .o_list_record_selector input`,
            run: "click",
        },
        ...editPageUrl("/edit-url-page", "/edit-url-cancelled", "Cancel"),
        // Starting from "/edit-url-page" again checks that the cancel kept it.
        ...editPageUrl("/edit-url-page", "/edit-url-updated", "Update"),
        {
            content: "Check that the URL has been updated",
            trigger: `${pageUrlCell}:contains(/edit-url-updated)`,
        },
    ],
});
