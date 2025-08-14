import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { dragenterFiles } from "@web/../tests/utils";

function getMeetingViewTourSteps({ inWelcomePage = false } = {}) {
    const steps = [
        { trigger: ".o-mail-Meeting" },
        {
            trigger: ".o-mail-Meeting [title='Invite People']",
            run: "click",
        },
        { trigger: ".o-mail-Meeting .o-mail-ActionPanel:contains('Invite people')" },
        {
            trigger: ".o-mail-Meeting [title='Invite People']", // close it
            run: "click",
        },
        { trigger: ".o-mail-Meeting:not(:has(.o-mail-ActionPanel))" },
        {
            trigger: ".o-mail-Meeting [title='Invite People']",
            run: "click",
        },
        { trigger: ".o-mail-Meeting .o-mail-ActionPanel:contains('Invite people')" },
        {
            trigger: ".o-mail-Meeting [title='Chat']",
            run: "click",
        },
        {
            trigger:
                ".o-mail-Meeting .o-mail-ActionPanel .o-mail-Thread:contains('john (base.group_user) and bob (base.group_user)')",
            async run({ waitFor }) {
                const files = [new File(["hi there"], "file2.txt", { type: "text/plain" })];
                await dragenterFiles(".o-mail-Meeting .o-mail-ActionPanel", files);
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
            trigger: ".o-mail-Meeting [title='Exit Fullscreen']",
            run: "click",
        },
        { trigger: "body:not(:has(.o-mail-Meeting))" },
    ];
    if (inWelcomePage) {
        steps.unshift({ trigger: "[title='Join Channel']", run: "click" });
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
        steps: () => getMeetingViewTourSteps({ inWelcomePage: true }),
    });
