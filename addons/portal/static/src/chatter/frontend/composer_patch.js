import { Composer } from "@mail/core/common/composer";

import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, {
    setup() {
        super.setup();
        if (!this.thread || this.thread.model !== "discuss.channel") {
            this.suggestion = undefined;
        }
    },

    get postData() {
        const postData = super.postData;
        postData.extraData = { ...postData.extraData, ...this.thread.securityParams };
        return postData;
    },
});
