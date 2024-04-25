import { messageActionsRegistry } from "@mail/core/common/message_actions";

import { patch } from "@web/core/utils/patch";

const downloadFilesAction = messageActionsRegistry.get("download_files");
patch(downloadFilesAction, {
    condition(component) {
        return component.message.thread?.type !== "chatter" && super.condition(component);
    },
});
