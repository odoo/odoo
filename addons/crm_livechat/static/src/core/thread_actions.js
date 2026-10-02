import { LivechatCommandDialog } from "@im_livechat/core/common/livechat_command_dialog";

import { registerThreadAction } from "@mail/core/common/thread_actions";
import "@mail/discuss/call/common/thread_actions";

import { _t } from "@web/core/l10n/translation";

registerThreadAction("create-lead", {
    condition: false, // managed by ThreadAction patch
    icon: "handshake",
    name: _t("Create Lead"),
    panel: {
        component: LivechatCommandDialog,
        props: ({ thread }) => ({
            commandName: "lead",
            placeholderText: _t("e.g. Product pricing"),
            thread,
            title: _t("Create Lead"),
            icon: "handshake",
        }),
    },
    sequence: 10,
    sequenceGroup: 25,
});
