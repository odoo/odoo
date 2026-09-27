import { Composer } from "@mail/core/common/composer";
import { useMaybePlugin } from "@mail/utils/common/hooks";
import { ProjectSharingPlugin } from "@project/project_sharing/chatter/project_sharing_plugin";
import { _t } from "@web/core/l10n/translation";

import { patch } from "@web/core/utils/patch";
import { onWillStart } from "@odoo/owl";

patch(Composer.prototype, {
    setup() {
        super.setup();
        this.projectSharingPlugin = useMaybePlugin(ProjectSharingPlugin);
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
        if (this.projectSharingPlugin?.projectSharingId()) {
            extraData.project_sharing_id = this.projectSharingPlugin.projectSharingId();
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
