import { Composer } from "@mail/core/common/composer";

import { patch } from "@web/core/utils/patch";

/** @type {Composer} */
const composerPatch = {
    async sendGifMessage(gif) {
        await this._sendMessage(gif.url, {
            parentId: this.props.messageToReplyTo?.message?.id,
        });
    },
};
patch(Composer.prototype, composerPatch);
