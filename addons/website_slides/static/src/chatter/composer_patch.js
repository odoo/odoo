/* @odoo-module */

import { Composer } from "@mail/core/common/composer";

import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, {
    get isSendButtonDisabled() {
        const model = this.thread?.model ?? this.message.model;
        return model !== "slide.channel" && super.isSendButtonDisabled;
    },
});
