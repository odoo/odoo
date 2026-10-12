import {
    clickOnSnippet,
    insertSnippet,
    openPowerbox,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "website_powerbox_snippet",
    {
        edition: true,
    },
    () => [
        ...insertSnippet({
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
        openPowerbox(":iframe .s_text_block p:last-child"),
        {
            content: "Click on the alert snippet",
            trigger: ".o-we-powerbox .o-we-command:contains('Alert')",
            run: "click",
        },
        {
            content: "Check if s_alert snipept is inserted",
            trigger: ":iframe .s_alert",
        },
    ]
);

registerWebsitePreviewTour(
    "website_powerbox_keyword",
    {
        edition: true,
    },
    () => [
        ...insertSnippet({
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
        openPowerbox(":iframe .s_text_block p:last-child"),
        {
            content: "Initially alert snippet should be present in the powerbox",
            trigger: ".o-we-powerbox .o-we-command:contains('Alert')",
        },
        {
            content:
                "Change the content to '/table' so that alert snippet should not be present in the powerbox",
            trigger: ":iframe .s_text_block p:last-child",
            run() {
                const wrapwrapEl = this.anchor.closest("#wrapwrap");
                this.anchor.textContent = "/table";
                wrapwrapEl.ownerDocument.dispatchEvent(
                    new KeyboardEvent("keyup", {
                        key: "DummyKey",
                        code: "KeyDummy",
                        cancelable: true,
                    })
                );
            },
        },
        {
            content: "Alert snippet should not be present in the powerbox",
            trigger: ".o-we-powerbox .o-we-command:not(:contains('Alert'))",
        },
        {
            content: "Change the content to '/banner'",
            trigger: ":iframe .s_text_block p:last-child",
            run() {
                const wrapwrapEl = this.anchor.closest("#wrapwrap");
                this.anchor.textContent = "/banner";
                wrapwrapEl.ownerDocument.dispatchEvent(
                    new KeyboardEvent("keyup", {
                        key: "DummyKey",
                        code: "KeyDummy",
                        cancelable: true,
                    })
                );
            },
        },
        {
            content: "Alert snippet should be present in the powerbox",
            trigger: ".o-we-powerbox .o-we-command:contains('Alert')",
        },
        {
            content: "Click on the alert snippet",
            trigger: ".o-we-powerbox .o-we-command:contains('Alert')",
            run: "click",
        },
        {
            content: "Check if s_alert snippet is inserted",
            trigger: ":iframe .s_alert",
        },
    ]
);
