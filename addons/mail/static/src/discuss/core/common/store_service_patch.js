/* @odoo-module */

import { Store } from "@mail/core/common/store_service";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const storePatch = {
    onLinkFollowed(fromThread) {
        if (!this.env.isSmall && fromThread?.model === "discuss.channel") {
            this.env.services["mail.thread"].open(fromThread, true, { autofocus: false });
        }
    },
};
patch(Store.prototype, storePatch);
