import { Composer } from "@mail/core/common/composer";

import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, {
    postData(composer) {
        const postData = super.postData(composer);
        if (this.env.projectSharingId) {
            postData.extraData = {
                ...postData.extraData,
                project_sharing_id: this.env.projectSharingId,
            };
        }
        return postData;
    },

    get isSendButtonDisabled() {
        return !this.thread.id || super.isSendButtonDisabled;
    },

    get allowUpload() {
        return this.thread.id && super.allowUpload;
    },
});
