/** @odoo-module */

/**
 * Project Task history tour.
 * Features tested:
 * - Create / edit a task description and ensure revisions are created on write
 * - Open the history dialog and check that the revisions are correctly shown
 * - Select a revision and check that the content / comparison are correct
 * - Click the restore button and check that the content is correctly restored
 */

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

const baseDescriptionContent = "Test project task history version";
const descriptionField = "div.note-editable.odoo-editor-editable.odoo-editor-qweb p";
function changeDescriptionContentAndSave(newContent) {
    const newText = `${baseDescriptionContent} ${newContent}`;
    return [ {
        trigger: descriptionField,
        run: async function(actions) {
            const textTriggerElement = this.anchor.querySelector(descriptionField);
            actions.editor(newText, textTriggerElement);
            await new Promise((r) => setTimeout(r, 300));
        },
    }, {
        trigger: "button.o_form_button_save",
    }];
}

registry.category("web_tour.tours").add("project_task_history_tour", {
    test: true,
    url: "/web",
    steps: () => [stepUtils.showAppsMenuItem(), {
        content: "Open the project app",
        trigger: ".o_app[data-menu-xmlid='project.menu_main_pm']",
    }, {
        content: "Open Test History Project",
        trigger: "div span.o_text_overflow[title='Test History Project']",
        extra_trigger: ".o_kanban_view",
    }, {
        content: "Open Test History Task",
        trigger: "div strong.o_kanban_record_title:contains('Test History Task')",
    },
        // edit the description content 3 times and save after each edit
        ...changeDescriptionContentAndSave("0"),
        ...changeDescriptionContentAndSave("1"),
        ...changeDescriptionContentAndSave("2"),
        ...changeDescriptionContentAndSave("3"),
    {
        content: "Go back to kanban view of tasks. this step is added because it takes some time to save the changes, so it's a sort of timeout to wait a bit for the save",
        trigger: ".o_back_button a",
    }, {
        content: "Open Test History Task",
        trigger: "div strong.o_kanban_record_title:contains('Test History Task')",
        extra_trigger: ".o_kanban_view",
    }, {
        content: "Open History Dialog",
        trigger: ".o_cp_action_menus i.fa-cog",
        extra_trigger: ".o_form_view",
    }, {
        content: "Open History Dialog",
        trigger: ".o_menu_item i.fa-history",
        extra_trigger: ".dropdown-menu",
    }, {
        content: "Verify that 4 revisions are displayed (default empty description after the creation of the task + 3 edits)",
        trigger: ".html-history-dialog .revision-list .btn",
        run: function () {
            const items = document.querySelectorAll(".revision-list .btn");
            if (items.length !== 4) {
                throw new Error('Expect 4 Revisions in the history dialog, got ' + items.length);
            }
        },
    }, {
        content: "Verify that the active revision (revision 4) is related to the third edit",
        trigger: `.history-container .tab-pane:contains("${baseDescriptionContent} 2")`,
    }, {
        content: "Go to the third revision related to the second edit",
        trigger: '.html-history-dialog .revision-list .btn:nth-child(2)',
    }, {
        content: "Verify that the active revision is the one clicked in the previous step",
        trigger: `.history-container .tab-pane:contains("${baseDescriptionContent} 1")`,
    }, {
        content: "Go to comparison tab",
        trigger: ".history-container .nav-item:contains(Comparison) a",
    }, {
        content: "Verify comparaison text",
        trigger: ".history-container .tab-pane",
        run: function () {
            const comparaisonHtml = document.querySelector(".history-container .tab-pane").innerHTML;
            const correctHtml = `<p><removed>${baseDescriptionContent} 3</removed><added>${baseDescriptionContent} 1</added></p>`;
            if (comparaisonHtml !== correctHtml) {
                throw new Error(`Expect comparison to be ${correctHtml}, got ${comparaisonHtml}`);
            }
        }
    }, {
        content: "Click on Restore History btn to get back to the selected revision in the previous step",
        trigger: '.modal-footer .btn-primary:contains("Restore")',
    }, {
        content: "Verify the confirmation dialog is opened",
        trigger: '.modal-footer .btn-primary:contains("Restore")',
    }, {
        content: "Restore",
        trigger: 'button.btn-primary',
    }, {
        content: "Verify that the description contains the right text after the restore",
        trigger: `${descriptionField}`,
        run: function () {
            const p = this.anchor?.innerText;
            const expected = `${baseDescriptionContent} 1`;
            if (p !== expected) {
                throw new Error(`Expect description to be ${expected}, got ${p}`);
            }
        }
    }, {
        content: "Go back to projects view. this step is added because Tour can't be finished with an open form view in edition mode.",
        trigger: 'a[data-menu-xmlid="project.menu_projects"]',
    }, {
        content: "Verify that we are on kanban view",
        trigger: 'button.o_switch_view.o_kanban.active',
        isCheck: true,
    }
]});
