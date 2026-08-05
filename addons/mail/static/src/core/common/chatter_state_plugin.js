import { Plugin, signal, t } from "@odoo/owl";
import { incrementFn } from "@mail/utils/common/signal";
import { useService } from "@web/core/utils/hooks";

export const CHATTER_PANEL = Object.freeze({
    ATTACHMENT: "ATTACHMENT",
    NONE: "NONE",
    PINNED_MESSAGES: "PINNED_MESSAGES",
    SEARCH: "SEARCH",
});

export class ChatterStatePlugin extends Plugin {
    activePanel = signal(CHATTER_PANEL.NONE, {
        type: t.selection([
            CHATTER_PANEL.ATTACHMENT,
            CHATTER_PANEL.NONE,
            CHATTER_PANEL.PINNED_MESSAGES,
            CHATTER_PANEL.SEARCH,
        ]),
    });
    composerType = signal(false, {
        type: t.or([t.selection(["message", "note"]), t.literal(false)]),
    });
    isTopStickyPinned = signal(false);
    jumpThreadPresent = signal(0);
    showActivities = signal(true);
    showAttachmentLoading = signal(false);
    showScheduledMessages = signal(true);
    store = useService("mail.store");
    thread = signal(undefined, { type: t.instanceOf(this.store["mail.thread"]).optional() });

    incrementJumpThreadPresent = incrementFn(this.jumpThreadPresent);
}
