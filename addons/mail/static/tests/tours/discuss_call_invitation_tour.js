import { ChannelMember } from "@mail/discuss/core/common/channel_member_model";

import { registry } from "@web/core/registry";
import { patchWithCleanup } from "@web/../tests/helpers/utils";

registry.category("web_tour.tours").add("discuss_call_invitation.js", {
    steps: () => {
        // Call invitation is cancelled after 30s. Increase this delay for the test.
        patchWithCleanup(ChannelMember, { CANCEL_CALL_INVITE_DELAY: 1e6 });
        return [
            { trigger: ".o-discuss-CallInvitation" },
            {
                trigger:
                    ".o-mail-CallInvitation-avatar[title='View the bob (base.group_user) and john (base.group_user) channel']",
            },
            {
                trigger:
                    ".o-discuss-CallInvitation-channelName:contains('bob (base.group_user) and john (base.group_user)')",
            },
            {
                trigger:
                    ".o-discuss-CallInvitation-description:contains('Incoming call from bob (base.group_user)')",
            },
            {
                trigger: ".o-discuss-CallInvitation-cameraPreview:not(:visible)",
            },
            {
                trigger: ".o-discuss-CallInvitation button[title='Join Call']",
            },
            {
                trigger: ".o-discuss-CallInvitation button[title='Reject']",
            },
            {
                trigger: ".o-discuss-CallInvitation button[title='Show camera preview']",
                run: "click",
            },
            {
                trigger: ".o-discuss-CallInvitation-cameraPreview",
            },
            {
                trigger: ".o-discuss-CallInvitation-cameraPreview button[title='Turn camera on']",
            },
            {
                trigger: ".o-discuss-CallInvitation-cameraPreview button[title='Unmute']",
            },
            {
                trigger: ".o-discuss-CallInvitation-cameraPreview button[title='Video Settings']",
                run: "click",
            },
            {
                trigger: "label:contains('Blur background')",
            },
            {
                trigger: ".o-discuss-CallInvitation button[title='Hide camera preview']",
                run: "click",
            },
            {
                trigger: ".o-discuss-CallInvitation-cameraPreview:not(:visible)",
            },
        ];
    },
});
