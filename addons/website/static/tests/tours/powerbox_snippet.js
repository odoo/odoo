import {clickOnSnippet, dragNDrop, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour("website_powerbox_snippet",{
    edition: true,
    test: true,
},
() => [
...dragNDrop({
    id: "s_text_block",
    name: "Text",
    groupName: "Text",
}),
...clickOnSnippet({
    id: "s_text_block",
    name: "Text",
}),
{
    content: "Select the last paragraph",
    trigger: ":iframe .s_text_block p:last-child",
    run: "click",
},
{
    content: "Show the powerbox",
    trigger: ":iframe .s_text_block p:last-child",
    run(actions) {
        actions.editor(`/`);
        const wrapwrap = this.anchor.closest("#wrapwrap");
        wrapwrap.dispatchEvent(
            new InputEvent("input", {
                inputType: "insertText",
                data: "/",
            })
        );
    },
},
{
    content: "Click on the alert snippet",
    trigger: ".oe-powerbox-wrapper .oe-powerbox-commandWrapper:contains('Alert')",
    run: "click",
},
{
    content: "Check if s_alert snipept is inserted",
    trigger: ":iframe .s_alert",
},
{
    content: "Remove the alert snippet",
    trigger: ":iframe .s_alert",
    run(actions) {
        this.anchor.remove();
    },
},
{
    content: "Show the powerbox",
    trigger: ":iframe .s_text_block p:last-child",
    run(actions) {
        actions.editor(`/`);
        const wrapwrap = this.anchor.closest("#wrapwrap");
        wrapwrap.dispatchEvent(
            new InputEvent("input", {
                inputType: "insertText",
                data: "/",
            })
        );
    },
},
{
    content: "Change the content to '/banner'",
    trigger: ":iframe .s_text_block p:last-child",
    run() {
        const wrapwrap = this.anchor.closest("#wrapwrap");
        this.anchor.textContent = "/banner";
        wrapwrap.ownerDocument.dispatchEvent(
            new KeyboardEvent('keyup', {
                key: 'DummyKey',
                code: 'KeyDummy',
                cancelable: true,
            })
        );
    },
},
{
    content: "Click on the alert snippet",
    trigger: ".oe-powerbox-wrapper .oe-powerbox-commandWrapper:contains('Alert')",
    run: "click",
},
{
    content: "Check if s_alert snipept is inserted",
    trigger: ":iframe .s_alert",
}
]);
