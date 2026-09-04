import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

/** Pathname of the channel invitation link, which holds the channel secret token. */
function getInvitationPathname() {
    /** @type {import("models").Store} */
    const store = odoo.__WOWL_DEBUG__.root.env.services["mail.store"];
    return new URL(store.discuss.thread.channel.invitationLink).pathname;
}

function getMeetingViewTourSteps({ isPublicPage = false } = {}) {
    const steps = [
        { trigger: ".o-mail-Meeting" },
        {
            trigger: ".o-mail-Meeting [title='Members']",
            run: "click",
        },
        { trigger: ".o-mail-Meeting .o-mail-ActionPanel:contains('Members')" },
        {
            trigger: ".o-mail-Meeting [title='Members']", // close it
            run: "click",
        },
        { trigger: ".o-mail-Meeting:not(:has(.o-mail-ActionPanel))" },
        {
            trigger: ".o-mail-Meeting [title='Members']",
            run: "click",
        },
        { trigger: ".o-mail-Meeting .o-mail-ActionPanel:contains('Members')" },
        {
            trigger: ".o-mail-Meeting [title='Chat']",
            run: "click",
        },
        {
            trigger:
                ".o-mail-Meeting .o-mail-ActionPanel .o-mail-Thread:contains('Meeting, Jan 1')",
        },
        {
            trigger: ".o-mail-Meeting .o-mail-ActionPanel .o-mail-Composer-input",
            run: "click",
        },
        { trigger: ".o-mail-Meeting [title='Chat']:not(:has(.badge))" },
        {
            trigger: ".o-mail-Message[data-persistent]:contains('Hello everyone!')",
            run: "hover && click .o-mail-Meeting .o-mail-Message-actions button[title='Expand']",
        },
        {
            trigger: ".o-dropdown-item:contains('Mark as Unread')",
            run: "click",
        },
        { trigger: ".o-mail-Meeting [title='Chat']:has(.badge:contains(1))" },
        {
            trigger: ".o-mail-Thread-banner span:contains('Mark as Read')",
            run: "click",
        },
        {
            trigger: ".o-mail-Meeting [title='Chat']:not(:has(.badge))",
        },
        {
            trigger: ".o-mail-Meeting .o-mail-ActionPanel",
            async run({ dragFiles, waitFor }) {
                const files = [new File(["hi there"], "file2.txt", { type: "text/plain" })];
                await dragFiles(files);
                // Ensure other dropzones such as discuss or chat window dropzones are not active in meeting view.
                await waitFor(".o-Dropzone", { only: true });
            },
        },
        {
            trigger: ".o-mail-Meeting [title='Close panel']",
            run: "click",
        },
        { trigger: ".o-mail-Meeting:not(:has(.o-mail-ActionPanel))" },
        {
            trigger: ".o-mail-Meeting",
            run: "press Escape",
        },
        { trigger: "body:not(:has(.o-mail-Meeting))" },
    ];
    if (isPublicPage) {
        steps.unshift(
            {
                trigger: ".modal:has(button:text('Use microphone')) .btn-close",
                run: "click",
            },
            { trigger: "input[name='guest_name']", run: "edit Guest" },
            { trigger: "[title='Join Channel']", run: "click" },
            {
                trigger: ".o-mail-Meeting",
                run() {
                    if (window.location.pathname !== getInvitationPathname()) {
                        console.error(
                            `Meeting view should show the invitation link, got "${window.location.pathname}".`
                        );
                    }
                },
            }
        );
        steps.push({
            trigger: "body:not(:has(.o-mail-Meeting))",
            run() {
                if (window.location.pathname === getInvitationPathname()) {
                    console.error(
                        "Leaving the meeting view should remove the invitation link from the URL."
                    );
                }
            },
        });
    }
    return steps;
}

registry
    .category("web_tour.tours")
    .add("discuss.meeting_view_tour", {
        steps: () => {
            // Avoid starting with mic/camera to prevent an unhandleable browser permission popup.
            browser.localStorage.setItem("discuss_call_preview_join_mute", "true");
            browser.localStorage.setItem("discuss_call_preview_join_video", "false");
            return getMeetingViewTourSteps();
        },
    })
    .add("discuss.meeting_view_public_tour", {
        steps: () => getMeetingViewTourSteps({ isPublicPage: true }),
    });
