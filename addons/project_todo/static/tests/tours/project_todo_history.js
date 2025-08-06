import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

const baseDescriptionContent = "Test project todo history version";
const descriptionField = `div.note-editable.odoo-editor-editable div.o-paragraph`;
function changeDescriptionContentAndSave(newContent) {
    const newText = `${baseDescriptionContent} ${newContent}`;
    return [
        {
            // force focus on editable so editor will create initial p (if not yet done)
            trigger: "div.note-editable.odoo-editor-editable",
            run: "click",
        },
        {
            trigger: descriptionField,
            run: `editor ${newText}`,
        },
        {
            trigger: "button.o_form_button_save",
            run: "click",
        },
        {
            content: "Wait the form is saved",
            trigger: ".o_form_saved",
        },
    ];
}

registry.category("web_tour.tours").add("project_todo_history_tour", {
    url: "/odoo",
    steps: () => [stepUtils.showAppsMenuItem(), {
        content: "Open the Todo app",
        trigger: ".o_app[data-menu-xmlid='project_todo.menu_todo_todos']",
        run: "click",
    },
    {
        content: "Open Test Todo",
        trigger: ".o_kanban_view .o_kanban_record:contains(Test History Todo)",
        run: "click",
    },
        // edit the description content 3 times and save after each edit
        ...changeDescriptionContentAndSave("0"),
        ...changeDescriptionContentAndSave("1"),
        ...changeDescriptionContentAndSave("2"),
        ...changeDescriptionContentAndSave("3"),
    {
        content: "Go back to kanban view of todos. this step is added because it takes some time to save the changes, so it's a sort of timeout to wait a bit for the save",
        trigger: ".o_back_button a",
        run: "click",
    },
    {
        content: "Open Test Todo",
        trigger: ".o_kanban_view .o_kanban_record:contains(Test History Todo)",
        run: "click",
    },
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
        trigger: ".o_menu_item i.fa-history",
        run: "click",
    }, {
        content: "Verify that 4 revisions are displayed (default empty description after the creation of the todo + 3 edits)",
        trigger: ".modal .html-history-dialog .revision-list .btn",
        run: function () {
            const items = document.querySelectorAll(".revision-list .btn");
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
        trigger: ".modal .html-history-dialog .revision-list .btn:nth-child(2)",
        run: "click",
    }, {
        content: "Verify that the active revision is the one clicked in the previous step",
        trigger: `.modal .history-container .tab-pane:contains("${baseDescriptionContent} 1")`,
        run: "click",
    }, {
        content: "Go to comparison tab",
        trigger: ".modal .history-container .nav-item:contains(Comparison) button",
        run: "click",
    }, {
        content: "Verify comparaison text",
        trigger: ".modal .history-container .tab-pane",
        run: function () {
            const comparaisonHtml = this.anchor.innerHTML;
            const correctHtml = `<added>${baseDescriptionContent} 1</added><removed>${baseDescriptionContent} 3</removed>`;
            if (!comparaisonHtml.includes(correctHtml)) {
                console.error(`Expect comparison to be ${correctHtml}, got ${comparaisonHtml}`);
            }
        },
    }, {
        content: "Click on Restore History btn to get back to the selected revision in the previous step",
        trigger: ".modal button.btn-primary:contains(/^Restore history$/)",
        run: "click",
    }, {
        content: "Verify the confirmation dialog is opened",
        trigger: ".modal button.btn-primary:contains(/^Restore$/)",
        run: "click",
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
        trigger: "button.o_form_button_save",
        run: "click",
    }, {
        content: "Wait the form is saved",
        trigger: ".o_form_saved",
    },
]});
