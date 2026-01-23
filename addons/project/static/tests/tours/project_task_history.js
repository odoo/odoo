/**
 * Project Task history tour.
 * Features tested:
 * - Create / edit a task description and ensure revisions are created on write
 * - Open the history dialog and check that the revisions are correctly shown
 * - Select a revision and check that the content / comparison are correct
 * - Click the restore button and check that the content is correctly restored
 */

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

const baseDescriptionContent = "Test project task history version";
function changeDescriptionContentAndSave(newContent) {
    const newText = `${baseDescriptionContent} ${newContent}`;
    return [
        {
            // force focus on editable so editor will create initial p (if not yet done)
            trigger: "div.note-editable.odoo-editor-editable",
            run: "click",
        },
        {
            trigger: `div.note-editable[spellcheck='true'].odoo-editor-editable`,
            run: `editor ${newText}`,
        },
        ...stepUtils.saveForm(),
    ];
}

function insertEditorContent(newContent) {
    return [
        {
            // force focus on editable so editor will create initial p (if not yet done)
            trigger: "div.note-editable.odoo-editor-editable",
            run: "click",
        },
        {
            trigger: `div.note-editable[spellcheck='true'].odoo-editor-editable`,
            run: async function () {
                // Insert content as html and make the field dirty
                const div = document.createElement("div");
                div.appendChild(document.createTextNode(newContent));
                this.anchor.removeChild(this.anchor.firstChild);
                this.anchor.appendChild(div);
                this.anchor.dispatchEvent(new Event("input", { bubbles: true }));
            },
        },
    ];
}

registry.category("web_tour.tours").add("project_task_history_tour", {
    url: "/odoo?debug=1,tests",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open the project app",
            trigger: ".o_app[data-menu-xmlid='project.menu_main_pm']",
            run: "click",
        },
        {
            content: "Open Test History Project",
            trigger: ".o_kanban_view .o_kanban_record:contains(Test History Project)",
            run: "click",
        },
        {
            content: "Open Test History Task",
            trigger: ".o_kanban_view .o_kanban_record:contains(Test History Task)",
            run: "click",
        },
        // edit the description content 3 times and save after each edit
        ...changeDescriptionContentAndSave("0"),
        ...changeDescriptionContentAndSave("1"),
        ...changeDescriptionContentAndSave("2"),
        ...changeDescriptionContentAndSave("3"),
        {
            content: "Open History Dialog",
            trigger: ".o_form_view .o_cp_action_menus i.fa-cog",
            run: "click",
        },
        {
            trigger: ".dropdown-menu",
        },
        {
            content: "Open History Dialog",
            trigger: ".o_popover .o_menu_item:has(i.fa-history):contains(Version history)",
            run: "click",
        },
        {
            content:
                "Verify that 5 revisions are displayed (default empty description after the creation of the task + 3 edits + current version)",
            trigger:
                ".modal .html-history-dialog.html-history-loaded .o_revision_panel .list-group-item:count(5)",
        },
        {
            content:
                "Verify that the active revision (revision 4) is related to the current version",
            trigger: `.modal .history-container .history-content-view .history-view-inner:contains(${baseDescriptionContent} 3)`,
        },
        {
            content: "Go to the third revision related to the second edit",
            trigger:
                ".modal .html-history-dialog.html-history-loaded .o_revision_panel .list-group-item:nth-child(3)",
            run: "click",
        },
        {
            content: "Verify that the active revision is the one clicked in the previous step",
            trigger: `.modal .history-container .history-content-view .history-view-inner:contains(${baseDescriptionContent} 1)`,
        },
        {
            content: "click on the comparison tab",
            trigger: ".history-container .history-view-top-bar label:contains(Show comparison)",
            run: "click",
        },
        {
            content: "Verify comparison text",
            trigger: `.modal .history-container .history-comparison-view
                :has(added:contains(Test project task history version 3))
                :has(removed:contains(Test project task history version 1))
            `,
        },
        {
            content:
                "Click on Restore History btn to get back to the selected revision in the previous step",
            trigger: ".modal button.btn-primary:contains(restore history)",
            run: "click",
        },
        {
            content: "Verify the confirmation dialog is opened",
            trigger:
                ".modal:has(.modal-title:contains(Are you sure you want to restore this version ?)) button.btn-primary:text(Restore)",
            run: "click",
        },
        {
            content: "Verify that the description contains the right text after the restore",
            trigger: `div.note-editable.odoo-editor-editable:contains(Test project task history version 1)`,
        },
        {
            content: "Go back to projects view.",
            trigger: 'a[data-menu-xmlid="project.menu_projects"]',
            run: "click",
        },
        {
            trigger: ".o_kanban_view",
        },
        {
            content: "Open Test History Project Without Tasks",
            trigger: ".o_kanban_view .o_kanban_record:contains(Without tasks project)",
            run: "click",
        },
        {
            trigger: ".o_kanban_project_tasks",
        },
        {
            content: "Switch to list view",
            trigger: ".o_switch_view.o_list",
            run: "click",
        },
        {
            content: "Create a new task.",
            trigger: '.o_list_button_add',
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
            trigger: 'div[name="name"] .o_input',
            content: 'Set task name',
            run: 'edit New task',
        },
        ...stepUtils.saveForm(),
        ...changeDescriptionContentAndSave("0"),
        ...changeDescriptionContentAndSave("1"),
        ...changeDescriptionContentAndSave("2"),
        ...changeDescriptionContentAndSave("3"),
        {
            trigger: ".o_form_view",
        },
        {
            content: "Open History Dialog",
            trigger: ".o_cp_action_menus i.fa-cog",
            run: "click",
        },
        {
            trigger: ".dropdown-menu",
        },
        {
            content: "Open History Dialog",
            trigger: ".o_menu_item i.fa-history",
            run: "click",
        },
        {
            content: "Close History Dialog",
            trigger: ".modal-header .btn-close",
            run: "click",
        },
        {
            content: "Go back to projects view. this step is added because Tour can't be finished with an open form view in edition mode.",
            trigger: 'a[data-menu-xmlid="project.menu_projects"]',
            run: "click",
        },
        {
            content: "Verify that we are on kanban view",
            trigger: 'button.o_switch_view.o_kanban.active',
        },
    ],
});

registry.category("web_tour.tours").add("project_task_last_history_steps_tour", {
    undeterministicTour_doNotCopy: true, // Remove this key to make the tour failed. ( It removes delay between steps )
    url: "/odoo?debug=1,tests",
    steps: () => [stepUtils.showAppsMenuItem(), {
        content: "Open the project app",
        trigger: ".o_app[data-menu-xmlid='project.menu_main_pm']",
        run: "click",
    },
    {
        content: "Open Test History Project",
        trigger: ".o_kanban_view .o_kanban_record:contains(Test History Project)",
        run: "click",
    },
    {
        content: "Open Test History Task",
        trigger: ".o_kanban_view .o_kanban_record:contains(Test History Task)",
        run: "click",
    },
        ...insertEditorContent("0"),
        ...stepUtils.saveForm(),
    {
        content: "Open History Dialog",
        trigger: ".o_cp_action_menus i.fa-cog",
        run: "click",
    }, {
        trigger: ".dropdown-menu",
    }, {
        content: "Open History Dialog",
        trigger: ".o_menu_item i.fa-history",
        run: "click",
    }, {
        trigger: ".modal .html-history-dialog.html-history-loaded",
    }, {
        content: "Verify that 2 revisions are displayed",
        trigger: ".modal .html-history-dialog .o_revision_panel .list-group-item:count(2)",
    }, {
        content: "Go to the second revision related to the initial blank document ",
        trigger: ".modal .html-history-dialog .o_revision_panel .list-group-item:nth-child(2)",
        run: "click",
    }, {
        trigger: ".modal .html-history-dialog.html-history-loaded",
    }, {
        trigger: '.modal button.btn-primary:enabled',
        run: "click",
    }, {
        trigger: '.modal button.btn-primary:text(Restore)',
        run: "click",
    },
        ...insertEditorContent("2"),
        ...stepUtils.saveForm(),
        ...insertEditorContent("4"),
    {
        trigger: ".o_notebook_headers li:nth-of-type(2) button",
        run: "click",
    },
    {
        trigger: ".o_notebook_headers li:nth-of-type(1) button",
        run: "click",
    },
        ...insertEditorContent("5"),
        ...stepUtils.saveForm(),
    ],
});
