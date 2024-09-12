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
const descriptionField = "div.note-editable.odoo-editor-editable p";
function changeDescriptionContentAndSave(newContent) {
    const newText = `${baseDescriptionContent} ${newContent}`;
    return [ {
        // force focus on editable so editor will create initial p (if not yet done)
        trigger: "div.note-editable.odoo-editor-editable",
        run: "click",
    }, {
        trigger: descriptionField,
        run: async function(actions) {
            const textTriggerElement = this.anchor.querySelector(descriptionField);
            actions.editor(newText, textTriggerElement);
            await new Promise((r) => setTimeout(r, 300));
        },
    }, {
        trigger: "button.o_form_button_save",
        run: "click",
    }];
}

registry.category("web_tour.tours").add("project_task_history_tour", {
    test: true,
    url: "/odoo",
    steps: () => [stepUtils.showAppsMenuItem(), {
        content: "Open the project app",
        trigger: ".o_app[data-menu-xmlid='project.menu_main_pm']",
        run: "click",
    },
    {
        trigger: ".o_kanban_view",
    },
    {
        content: "Open Test History Project",
        trigger: "div span.o_text_overflow[title='Test History Project']",
        run: "click",
    }, {
        content: "Open Test History Task",
        trigger: ".o_kanban_record:contains('Test History Task')",
        run: "click",
    },
        // edit the description content 3 times and save after each edit
        ...changeDescriptionContentAndSave("0"),
        ...changeDescriptionContentAndSave("1"),
        ...changeDescriptionContentAndSave("2"),
        ...changeDescriptionContentAndSave("3"),
    {
        content: "Go back to kanban view of tasks. this step is added because it takes some time to save the changes, so it's a sort of timeout to wait a bit for the save",
        trigger: ".o_back_button a",
        run: "click",
    },
    {
        trigger: ".o_kanban_view",
    },
    {
        content: "Open Test History Task",
        trigger: ".o_kanban_record:contains('Test History Task')",
        run: "click",
    },
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
    }, {
        content: "Verify that 4 revisions are displayed (default empty description after the creation of the task + 3 edits)",
        trigger: ".html-history-dialog .revision-list .revision-list-detail",
        run: function () {
            const items = document.querySelectorAll(".revision-list .revision-list-detail");
            if (items.length !== 4) {
                throw new Error('Expect 4 Revisions in the history dialog, got ' + items.length);
            }
        },
    }, {
        content: "Verify that the active revision (revision 4) is related to the third edit",
        trigger: `.modal .history-container .tab-pane:contains("${baseDescriptionContent} 2")`,
        run: "click",
    }, {
        content: "Go to the third revision related to the second edit",
        trigger: ".html-history-dialog .revision-list .revision-list-detail:nth-child(3)",
        run: "click",
    }, {
        content: "Verify that the active revision is the one clicked in the previous step",
        trigger: `.modal .history-container .tab-pane:contains("${baseDescriptionContent} 1")`,
        run: "click",
    }, {
        content: "Go to comparison tab",
        trigger: ".modal .history-container .nav-item:contains(Comparison) a",
        run: "click",
    }, {
        content: "Verify comparaison text",
        trigger: ".modal .history-container .tab-pane",
        run: function () {
            const comparaisonHtml = document.querySelector(".history-container .history-tab-content").innerHTML;
            const correctHtml = `<p><added>${baseDescriptionContent} 3</added><removed>${baseDescriptionContent} 1</removed></p>`;
            if (comparaisonHtml !== correctHtml) {
                throw new Error(`Expect comparison to be ${correctHtml}, got ${comparaisonHtml}`);
            }
        },
    }, {
        content: "Click on Restore History btn to get back to the selected revision in the previous step",
        trigger: ".modal:not(.o_inactive_modal) button.btn-primary:contains(/^Restore/)",
        run: "click",
    }, {
        content: "Verify the confirmation dialog is opened",
        trigger: ".modal:not(.o_inactive_modal) button.btn-primary:contains(/^Restore$/)",
        run: "click",
    }, {
        trigger: "body:not(:has(.modal))",
    }, {
        content: "Verify that the description contains the right text after the restore",
        trigger: descriptionField,
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
        run: "click",
    }, {
        content: "Verify that we are on kanban view",
        trigger: 'button.o_switch_view.o_kanban.active',
    }
]});
