import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

const baseDescriptionContent = "Test history version";
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

/**
 * Mail Template history tour.
 * Features tested:
 * - Create / edit a template body and ensure revisions are created on write
 * - Open the history dialog and check that the revisions are correctly shown
 * - Select a revision and check that the content / comparison are correct
 * - Click the restore button and check that the content is correctly restored
 */
registry.category("web_tour.tours").add("mail_template_history_tour", {
    test: true,
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: 'Go into the Settings "app"',
            trigger: '.o_app[data-menu-xmlid="base.menu_administration"]',
            run: "click",
        },
        {
            content: "Open email templates",
            trigger: 'button[name="open_mail_templates"]',
            run: "click",
        },
        {
            content: "Create a new email template",
            trigger: "button.o_list_button_add",
            run: "click",
        },
        {
            content: "Add a template name",
            trigger: "div[name=name] input",
            run: "edit History Template",
        },
        {
            content: 'Type "Contact" model',
            trigger: 'div[name="model_id"] input[type="text"]',
            run: "edit Contact",
        },
        {
            content: 'Select "Contact" model',
            trigger: 'a.dropdown-item:contains("Contact")',
            run: "click",
        },
        // edit the template body 3 times and save after each edit
        ...changeDescriptionContentAndSave("0"),
        ...changeDescriptionContentAndSave("1"),
        ...changeDescriptionContentAndSave("2"),
        ...changeDescriptionContentAndSave("3"),
        {
            trigger: "div.note-editable.odoo-editor-editable",
            content: "Wait for the changes to be saved",
            timeout: 3000,
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
        },
        {
            content: "Verify that 3 revisions are displayed (3 edits)",
            trigger: ".modal .html-history-dialog .revision-list .btn",
            run: function () {
                const items = document.querySelectorAll(".revision-list .btn");
                if (items.length !== 3) {
                    console.error("Expect 3 Revisions in the history dialog, got " + items.length);
                }
            },
        },
        {
            content: "Verify that the active revision (revision 3) is related to the second edit",
            trigger: `.modal .history-container .tab-pane:contains("${baseDescriptionContent} 2")`,
            run: "click",
        },
        {
            content: "Go to the second revision related to the first edit",
            trigger: ".modal .html-history-dialog .revision-list .btn:nth-child(2)",
            run: "click",
        },
        {
            content: "Verify that the active revision is the one clicked in the previous step",
            trigger: `.modal .history-container .tab-pane:contains("${baseDescriptionContent} 1")`,
            run: "click",
        },
        {
            content: "Go to comparison tab",
            trigger: ".modal .history-container .nav-item:contains(Comparison) a",
            run: "click",
        },
        {
            content: "Verify comparaison text",
            trigger: ".modal .history-container .tab-pane",
            run: function () {
                const comparaisonHtml = this.anchor.innerHTML;
                const correctHtml = `<added>${baseDescriptionContent} 1</added><removed>${baseDescriptionContent} 3</removed>`;
                if (!comparaisonHtml.includes(correctHtml)) {
                    console.error(`Expect comparison to be ${correctHtml}, got ${comparaisonHtml}`);
                }
            },
        },
        {
            content: "Click on Restore History btn to get back to the selected revision",
            trigger: ".modal button.btn-primary:contains(/^Restore history$/)",
            run: "click",
        },
        {
            content: "Verify the confirmation dialog is opened",
            trigger: ".modal button.btn-primary:contains(/^Restore$/)",
            run: "click",
        },
        {
            content: "Verify that the body contains the right text after the restore",
            trigger: `div.note-editable.odoo-editor-editable`,
            run: function () {
                const p = this.anchor?.innerText;
                const expected = `${baseDescriptionContent} 1`;
                if (p !== expected) {
                    console.error(`Expect body to be ${expected}, got ${p}`);
                }
            },
        },
    ],
});
