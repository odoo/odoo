import { Composer } from "@mail/core/common/composer";
import { _t } from "@web/core/l10n/translation";

import { patch } from "@web/core/utils/patch";
import { onWillStart } from "@odoo/owl";

patch(Composer.prototype, {
    setup() {
        super.setup();
        onWillStart(() => {
            if (this.thread && !this.thread.id) {
                this.state.active = false;
            }
        });
    },

    get placeholder() {
        if (this.ancestors.projectSharingId) {
            return _t("Write a message…");
        }
        return super.placeholder;
    },

    get extraData() {
        const extraData = super.extraData;
        if (this.ancestors.projectSharingId) {
            extraData.project_sharing_id = this.ancestors.projectSharingId;
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
