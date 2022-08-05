/** @odoo-module */

import wTourUtils from 'website.tour_utils';

wTourUtils.registerEditionTour('snippet_editor_panel_options', {
    test: true,
    url: '/',
    edition: true,
}, [
wTourUtils.dragNDrop({
    id: 's_text_image',
    name: 'Text - Image',
}), {
    content: "Click on the first paragraph.",
    trigger: 'iframe .s_text_image p',
}, {
    content: "The text toolbar should be visible. The paragraph should be selected.",
    trigger: '#oe_snippets .o_we_customize_panel > #o_we_editor_toolbar_container',
    run() {
        const iframeDocument = document.querySelector('.o_iframe').contentDocument;
        const pText = iframeDocument.querySelector('.s_text_image p').textContent;
        const selection = iframeDocument.getSelection().toString();
        if (pText !== selection) {
            console.error("The paragraph was not correctly selected.");
        }
    },
}, {
    content: "Click on the width option.",
    trigger: '[data-select-class="o_container_small"]',
}, {
    content: "The snippet should have the correct class.",
    trigger: 'iframe .s_text_image > .o_container_small',
    run: () => {}, // It's a check.
}, {
    content: "The text toolbar should still be visible, and the text still selected.",
    trigger: '#oe_snippets .o_we_customize_panel > #o_we_editor_toolbar_container',
    run() {
        const iframeDocument = document.querySelector('.o_iframe').contentDocument;
        const pText = iframeDocument.querySelector('.s_text_image p').textContent;
        const selection = iframeDocument.getSelection().toString();
        if (pText !== selection) {
            console.error("The paragraph text selection was lost.");
        }
    },
}, {
    content: "Click on the anchor option",
    trigger: '#oe_snippets .snippet-option-anchor we-button',
    run() {
        // The clipboard cannot be accessed from a script.
        // https://w3c.github.io/editing/docs/execCommand/#dfn-the-copy-command
        // The execCommand is patched for that step so that ClipboardJS still
        // sends the 'success' event.
        const oldExecCommand = document.execCommand;
        document.execCommand = () => true;
        this.$anchor[0].click();
        document.execCommand = oldExecCommand;
    }
}, {
    content: "Check the copied url from the notification toast",
    trigger: '.o_notification_manager .o_notification_content',
    run() {
        const { textContent } = this.$anchor[0];
        const url = textContent.substring(textContent.indexOf('/'));

        // The url should not target the client action
        if (url.startsWith('/@')) {
            console.error('The anchor option should target the frontend');
        }

        const iframeDocument = document.querySelector('.o_iframe').contentDocument;
        const snippetId = iframeDocument.querySelector('.s_text_image').id;
        if (!url || url.indexOf(snippetId) < 0) {
            console.error('The anchor option does not target the correct snippet.');
        }
    },
}]);
