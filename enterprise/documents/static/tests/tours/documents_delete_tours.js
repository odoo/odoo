/** @odoo-module **/

import { registry } from "@web/core/registry";

function restoreDocumentSteps() {
    return [
        {
            trigger: '.o_search_panel_label_title:contains("Trash")',
            content: "Open trash",
            run: "click",
        },
        {
            trigger: '.o_search_panel_field header.active:contains("Trash")',
            content: "Check that we are in the trash",
        },
        {
            trigger: '.o_kanban_record:contains("Chouchou")',
            content: "Select document",
            run: "click",
        },
        {
            trigger: ".o_control_panel_actions button:contains('Action')",
            run: "click",
        },
        {
            trigger: "button:contains('Restore')",
            run: "click",
        },
        {
            trigger: ".o_kanban_renderer:not(:has(.o_kanban_record:not(.o_kanban_ghost)))",
            content: "Check that the document is no longer visible",
        },
    ];
}

registry.category("web_tour.tours").add("document_delete_tour", {
    steps: () => [
        // Archive a file in a folder and restore it
        {
            trigger: '.o_search_panel_field header.active:contains("Folder1")',
            content: "Check that we are in Folder1",
        },
        {
            trigger: '.o_kanban_record:contains("Chouchou")',
            content: "Select a file",
            run: "click",
        },
        {
            trigger: '.o_record_selected:contains("Chouchou")',
        },
        {
            trigger: ".o_control_panel_actions button:contains('Action')",
            run: "click",
        },
        {
            trigger: "button:contains('Move to Trash')",
            run: "click",
        },
        {
            trigger: ".modal .modal-footer .btn-primary:contains(move to trash)",
            content: "Confirm deletion",
            run: "click",
        },
        {
            trigger: ".o_kanban_renderer:not(:has(.o_kanban_record:not(.o_kanban_ghost)))",
            content: "Check that the document is no longer visible",
        },
        ...restoreDocumentSteps(),
        // 2) Archive a folder (and this its documents) and restore the archived document
        {
            trigger: '.o_search_panel_field span:contains("Folder1")',
            content: "Go back to folder",
            run: "click",
        },
        {
            trigger: '.o_kanban_record:contains("Chouchou")',
            content: "Select a file",
            run: "click",
        },
        {
            trigger: ".o_control_panel_actions button:contains('Action')",
            run: "click",
        },
        {
            trigger: "button:contains('Move to Trash')",
            run: "click",
        },
        {
            trigger: ".modal .modal-footer .btn-primary:contains(move to trash)",
            content: "Confirm deletion",
            run: "click",
        },
        {
            trigger: ".o_kanban_renderer:not(:has(.o_kanban_record:not(.o_kanban_ghost)))",
            content: "Check that the document is no longer visible",
        },
        {
            trigger: '.o_search_panel_label_title:contains("Trash")',
            content: "Open trash",
            run: "click",
        },
        {
            trigger: '.o_search_panel_field header.active:contains("Trash")',
            content: "Check that we are in the trash",
        },
        {
            trigger: '.o_kanban_record:contains("Chouchou")',
            content: "Select document",
            run: "click",
        },
        {
            trigger: ".o_control_panel_actions button:contains('Action')",
            run: "click",
        },
        {
            trigger: "button:contains('Delete')",
            run: "click",
        },
        {
            trigger: ".modal-footer .btn-primary",
            content: "Confirm deletion",
            run: "click",
        },
        {
            trigger: ".o_kanban_renderer:not(:has(.o_kanban_record:not(.o_kanban_ghost)))",
            content: "Check that the document is no longer visible",
        },
        {
            trigger: '.o_search_panel_field header:contains("Folder1")',
            content: "Go back to folder one last time",
            run: "click",
        },
        {
            trigger: ".o_kanban_renderer:not(:has(.o_kanban_record:not(.o_kanban_ghost)))",
            content: "Check that the document is no longer visible",
        },
    ],
});

registry.category("web_tour.tours").add("document_default_access_view", {
    steps: () => [
        {
            trigger: '.o_record_selected:contains("Chouchou")',
            content: "Check that Chouchou is selected.",
        },
        {
            trigger: '.o_search_panel_category_value header.active:contains("All")',
            content: "Check that we are in the All folder.",
        },
    ],
});
