import { Composer } from "@mail/core/common/composer";

import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, {
    setup() {
        super.setup();
        if (!this.thread || this.thread.model !== "discuss.channel") {
            this.suggestion = undefined;
        }
    },

    postData(composer) {
        const postData = super.postData(composer);
        postData.options = { ...postData.options, ...this.env.portalSecurity };
        return postData;
    },
});
