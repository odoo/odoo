/** @odoo-module */

import { ThreadIcon } from "@mail/new/discuss/thread_icon";
import { Typing } from "@mail/new/composer/typing";

import { patch } from "@web/core/utils/patch";

Object.assign(ThreadIcon, {
    components: {
        ...ThreadIcon.components,
        Typing,
    },
});

patch(ThreadIcon.prototype, "im_livechat", {
    get classNames() {
        if (this.thread.type === "livechat") {
            return "fa fa-comments";
        }
        return this._super();
    },
});
