import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { dragenterFiles } from "@web/../tests/utils";

function getMeetingViewTourSteps({ inWelcomePage = false } = {}) {
    const steps = [
        { trigger: ".o-mail-Meeting" },
        {
            trigger: "[title='Invite people']",
            run: "click",
        },
        { trigger: ".o-mail-Meeting-sidePanel:contains('Invite people')" },
        {
            trigger: "[title='Close invite']",
            run: "click",
        },
        { trigger: ".o-mail-Meeting:not(:has(.o-mail-Meeting-sidePanel))" },
        {
            trigger: "[title='Invite people']",
            run: "click",
        },
        { trigger: ".o-mail-Meeting-sidePanel:contains('Invite people')" },
        {
            trigger: "[title='Chat']",
            run: "click",
        },
        {
            trigger:
                ".o-mail-Meeting-sidePanel .o-mail-Thread:contains('john (base.group_user) and bob (base.group_user)')",
            async run() {
                const files = [new File(["hi there"], "file2.txt", { type: "text/plain" })];
                await dragenterFiles(".o-mail-Meeting-sidePanel", files);
                const { waitFor } = odoo.loader.modules.get("@odoo/hoot-dom");
                // Ensure other dropzones such as discuss or chat window dropzones are not active in meeting view.
                await waitFor(".o-Dropzone", { only: true });
            },
        },
        {
            trigger: "[title='Close Side Panel']",
            run: "click",
        },
        { trigger: ".o-mail-Meeting:not(:has(.o-mail-Meeting-sidePanel))" },
        {
            trigger: "[title='Exit Fullscreen']",
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
