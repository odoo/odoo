import { Message } from "@mail/core/common/message";
import { maybePlugin } from "@mail/utils/common/misc";
import { ProjectSharingPlugin } from "@project/project_sharing/chatter/project_sharing_plugin";

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        this.projectSharingPlugin = maybePlugin(ProjectSharingPlugin);
    },
});
