/* @odoo-module */

import { Composer } from "@mail/core/common/composer";
import { Message as MessageModel } from "@mail/core/common/message_model";
import { Store } from "@mail/core/common/store_service";
import { Thread } from "@mail/core/common/thread_model";
import { fetchNewMessages, loadAround } from "@mail/core/common/thread_service";
import { patchFn } from "@mail/utils/common/patch";

import { patch } from "@web/core/utils/patch";

patchFn(fetchNewMessages, function (thread) {});
patchFn(loadAround, function () {});

patch(Composer.prototype, "im_livechat/disabled", {
    get allowUpload() {
        return false;
    },
});

patch(MessageModel.prototype, "im_livechat/disabled", {
    get hasActions() {
        return false;
    },
});

patch(Thread.prototype, "im_livechat/disabled", {
    get hasMemberList() {
        return false;
    },
});

patch(Store.prototype, "im_livechat/disabled", {
    setup() {
        this._super(...arguments);
        this.hasLinkPreviewFeature = false;
    },
});
