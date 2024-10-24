/* @odoo-module */

import { ThreadService } from "@mail/core/common/thread_service";
import { patch } from "@web/core/utils/patch";

/** @type {import("@mail/core/common/thread_service").ThreadService} */
patch(ThreadService.prototype, {
    _openChatWindow(
        thread,
        replaceNewMessageChatWindow,
        { autofocus = true, openMessagingMenuOnClose } = {}
    ) {
        if (!thread.is_pinned) {
            this.store.env.services["bus_service"].addChannel(thread.busChannel);
        }
        super._openChatWindow(...arguments);
    },
});
