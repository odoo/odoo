/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";

wTourUtils.registerWebsitePreviewTour("website_powerbox_snippet", {
    edition: true,
    test: true,
}, () => [
    wTourUtils.dragNDrop({
        id: "s_text_block",
        name: "Text",
    }), {
        content: "Check if s_text_block snippet is inserted",
        trigger: "iframe .s_text_block",
        run: () => {},
    }, {
        content: "Select the last paragraph",
        trigger: "iframe .s_text_block p:last-child",
    }, {
        content: "Show the powerbox",
        trigger: "iframe .s_text_block p:last-child",
        run: function(actions) {
            actions.text(`/`, this.$anchor[0]);
            const wrapwrapEl = this.$anchor[0].closest("#wrapwrap");
            wrapwrapEl.dispatchEvent(
                new InputEvent("input", {
                    inputType: "insertText",
                    data: "/",
                })
            );
        },
    }, {
        content: "Initially alert snippet should be present in the powerbox",
        trigger: ".oe-powerbox-wrapper .oe-powerbox-commandName:contains('Alert')",
        run: () => {},
    }, {
        content: "Change the content to '/table' so that alert snippet should not be present in the powerbox",
        trigger: "iframe .s_text_block p:last-child",
        run: function() {
            const wrapwrapEl = this.$anchor[0].closest("#wrapwrap");
            this.$anchor[0].textContent = "/table";
            wrapwrapEl.ownerDocument.dispatchEvent(
                new KeyboardEvent('keyup', {
                    key: 'DummyKey',
                    code: 'KeyDummy',
                    cancelable: true,
                })
            );
        },
    }, {
        content: "Alert snippet should not be present in the powerbox",
        trigger: ".oe-powerbox-wrapper .oe-powerbox-commandName:not(:contains('Alert'))",
        run: () => {},
    }, {
        content: "Change the content to '/banner'",
        trigger: "iframe .s_text_block p:last-child",
        run: function() {
            const wrapwrapEl = this.$anchor[0].closest("#wrapwrap");
            this.$anchor[0].textContent = "/banner";
            wrapwrapEl.ownerDocument.dispatchEvent(
                new KeyboardEvent('keyup', {
                    key: 'DummyKey',
                    code: 'KeyDummy',
                    cancelable: true,
                })
            );
        },
    }, {
        content: "Alert snippet should be present in the powerbox",
        trigger: ".oe-powerbox-wrapper .oe-powerbox-commandName:contains('Alert')",
        run: () => {},
    }, {
        content: "Click on the alert snippet",
        trigger: ".oe-powerbox-wrapper .oe-powerbox-commandName:contains('Alert')",
    }, {
        content: "Check if s_alert snippet is inserted",
        trigger: "iframe .s_alert",
        run: () => {},
    }
]);
