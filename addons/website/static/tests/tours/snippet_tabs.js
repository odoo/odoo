/** @odoo-module **/

import {
    registerWebsitePreviewTour,
    insertSnippet,
    changeOption,
} from '@website/js/tours/tour_utils';

registerWebsitePreviewTour("snippet_tabs", {
    edition: true,
    url: "/",
}, () => [
    ...insertSnippet({
        id: "s_tabs",
        name: "Tabs",
        groupName: "Content",
    }),
    {
        content: "Double click on the first tab link to select all the text",
        trigger: ":iframe .s_tabs .nav-link.active",
        run: "dblclick",
    },
    {
        content: "Change the text of the tab link",
        trigger: ":iframe .s_tabs .nav-link.active",
        run() {
            this.anchor.dispatchEvent(new InputEvent("input", {
                inputType: "insertText",
                bubbles: true,
                data: "Tab #1"
            }));
        },
    },
    {
        content: "Check that the first tab link is still there and has the new text",
        trigger: ":iframe .s_tabs .nav-link.active:contains('Tab #1')",
    },
    {
        content: "Double click on the third tab link to select all the text",
        trigger: ":iframe .s_tabs .nav-item:nth-of-type(3) .nav-link:not('.active')",
        run: "dblclick",
    },
    {
        content: "Remove the text of the tab link and add a new text",
        trigger: ":iframe .s_tabs .nav-item:nth-of-type(3) .nav-link.active:not(:contains('Tab #1'))",
        run() {
            this.anchor.dispatchEvent(new KeyboardEvent("keydown", {
                key: "Backspace",
                bubbles: true
            }));
            this.anchor.dispatchEvent(new InputEvent("input", {
                inputType: "insertText",
                bubbles: true,
                data: "Tab #3"
            }));
        },
    },
    {
        content: "Check that the third tab link is still there and has the new text",
        trigger: ":iframe .s_tabs .nav-item:nth-of-type(3) .nav-link.active:contains('Tab #3')",
    },
    changeOption("NavTabs", "we-button[data-remove-item]"),
    {
        content: "Check that only 2 tab panes remain",
        trigger: ":iframe .s_tabs .s_tabs_content",
        run() {
            if (this.anchor.querySelectorAll(".tab-pane").length !== 2) {
                console.error("There should be exactly 2 tab panes in the DOM.");
            }
        },
    },
    {
        content: "Check that the first tab link is active",
        trigger: ":iframe .s_tabs .nav-item:nth-of-type(1) .nav-link.active",
    },
    changeOption("NavTabs", "we-button[data-add-item]"),
    {
        content: "Check there are 3 tab panes",
        trigger: ":iframe .s_tabs .s_tabs_content",
        run() {
            if (this.anchor.querySelectorAll(".tab-pane").length !== 3) {
                console.error("There should be exactly 3 tab panes in the DOM.");
            }
        },
    },
]);
