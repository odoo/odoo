import {
    changeOption,
    changeOptionInPopover,
    clickOnSave,
    insertSnippet,
    goBackToBlocks,
    registerWebsitePreviewTour,
    selectFullText,
} from '@website/js/tours/tour_utils';
import { browser } from '@web/core/browser/browser';

const checkIfParagraphSelected = (trigger) => ({
    content: "Check if the paragraph is selected.",
    trigger: trigger,
    run() {
        const pText = this.anchor.textContent;
        const selection = this.anchor.ownerDocument.getSelection().toString();
        if (pText !== selection) {
            console.error("The paragraph was not correctly selected.");
        }
    },
});

const checkIfTextToolbarVisible = {
    content: "Check if the text toolbar is visible",
    trigger: ".o-we-toolbar",
};

registerWebsitePreviewTour('snippet_editor_panel_options', {
    url: '/',
    edition: true,
}, () => [
...insertSnippet({
    id: 's_text_image',
    name: 'Text - Image',
    groupName: "Content",
}),
// Test keeping the text selection when using the width option.
selectFullText("first paragraph", ".s_text_image p"),
checkIfParagraphSelected(":iframe .s_text_image p"),
checkIfTextToolbarVisible,
{
    content: "Click on the width option.",
    trigger: "[data-action-param='o_container_small']",
    run: "click",
}, {
    content: "The snippet should have the correct class.",
    trigger: ':iframe .s_text_image > .o_container_small',
},
checkIfParagraphSelected(":iframe .s_text_image p"),
// Test the anchor option.
{
    content: "Click on the anchor option",
    trigger: "[data-container-title='Text - Image'] .oe_snippet_anchor",
    async run(helpers) {
        // Patch and ignore write on clipboard in tour as we don't have permissions
        const oldWriteText = browser.navigator.clipboard.writeText;
        browser.navigator.clipboard.writeText = () => { console.info('Copy in clipboard ignored!') };
        await helpers.click();
        // Restore the writeText after a short delay to avoid reverting it
        // before the plugin function has been completed
        await new Promise(resolve => setTimeout(resolve, 100));
        browser.navigator.clipboard.writeText = oldWriteText;
    }
}, {
    content: "Check the copied url from the notification toast",
    trigger: '.o_notification_manager .o_notification_content',
    run() {
        const { textContent } = this.anchor;
        const url = textContent.substring(textContent.indexOf('/'));

        // The url should not target the client action
        if (url.startsWith('/@')) {
            console.error('The anchor option should target the frontend');
        }

        const iframeDocument = document.querySelector(".o_iframe_container iframe").contentDocument;
        const snippetId = iframeDocument.querySelector('.s_text_image').id;
        if (!url || url.indexOf(snippetId) < 0) {
            console.error('The anchor option does not target the correct snippet.');
        }
    },
},
// Test keeping the text selection when adding columns to a snippet with none.
goBackToBlocks(),
...insertSnippet({
    id: 's_text_block',
    name: 'Text',
    groupName: "Text",
}),
selectFullText("first paragraph", ".s_text_block p"),
checkIfParagraphSelected(":iframe .s_text_block p"),
checkIfTextToolbarVisible,
...changeOptionInPopover("Text", "Layout", "[data-action-value='3']"),
{
    content: "The snippet should have the correct number of columns.",
    trigger: ':iframe .s_text_block .container > .row .col-lg-4:eq(3)',
    run() {
        if (this.anchor.childElementCount !== 3) {
            console.error("The snippet does not have the correct number of columns");
        }
    },
},
checkIfParagraphSelected(":iframe .s_text_block p"),
// Test keeping the text selection when removing all columns of a snippet.
...changeOptionInPopover("Text", "Layout", "[data-action-value='0']"),
{
    content: "The snippet should have the correct number of columns.",
    trigger: ':iframe .s_text_block .container:not(:has(.row))',
},
checkIfParagraphSelected(":iframe .s_text_block p"),
// Test keeping the text selection when toggling the grid mode.
changeOption("Text", "[data-action-id='setGridLayout']"),
{
    content: "The snippet row should have the grid mode class.",
    trigger: ":iframe .s_text_block .row.o_grid_mode",
},
checkIfParagraphSelected(":iframe .s_text_block p"),
// Test keeping the text selection when toggling back the column mode.
changeOption("Text", "[data-action-id='setColumnLayout']"),
{
    content: "The snippet row should not have the grid mode class anymore.",
    trigger: ":iframe .s_text_block .row:not(.o_grid_mode)",
},
checkIfParagraphSelected(":iframe .s_text_block p"),
...clickOnSave(),
]);
