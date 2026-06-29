import { Composer } from "@mail/core/common/composer";
import { maybePlugin } from "@mail/utils/common/misc";
import { ProjectSharingPlugin } from "@project/project_sharing/chatter/project_sharing_plugin";
import { _t } from "@web/core/l10n/translation";

import { patch } from "@web/core/utils/patch";
import { onWillStart } from "@odoo/owl";

patch(Composer.prototype, {
    setup() {
        super.setup();
        this.projectSharingPlugin = maybePlugin(ProjectSharingPlugin);
        onWillStart(() => {
            if (this.thread && !this.thread.id) {
                this.state.active = false;
            }
        });
    },

    get placeholder() {
        if (this.projectSharingPlugin?.projectSharingId()) {
            return _t("Write a message…");
        }
        return super.placeholder;
    },

    get extraData() {
        const extraData = super.extraData;
        const projectSharingId = this.projectSharingPlugin?.projectSharingId();
        if (projectSharingId) {
            extraData.project_sharing_id = projectSharingId;
        }
        return extraData;
    },

    get isSendButtonDisabled() {
        if (this.thread && !this.thread.id) {
            return true;
        }
        return super.isSendButtonDisabled;
    },

    get allowUpload() {
        if (this.thread && !this.thread.id) {
            return false;
        }
        return super.allowUpload;
    },
});
