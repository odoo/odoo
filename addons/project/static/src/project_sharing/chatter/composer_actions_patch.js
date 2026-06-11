import { ComposerAction } from "@mail/core/common/composer_actions";
import { maybePlugin } from "@mail/utils/common/misc";
import { ProjectSharingPlugin } from "@project/project_sharing/chatter/project_sharing_plugin";

import { patch } from "@web/core/utils/patch";

patch(ComposerAction.prototype, {
    setup() {
        super.setup();
        this.projectSharingPlugin = maybePlugin(ProjectSharingPlugin);
    },
    _condition() {
        if (this.id === "open-full-composer" && this.projectSharingPlugin?.projectSharingId()) {
            return false;
        }
        return super._condition(...arguments);
    },
});
