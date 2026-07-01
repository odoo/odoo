import { Thread } from "@mail/core/common/thread_model";
import { fields } from "@mail/model/misc";

import { patch } from "@web/core/utils/patch";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

/** @type {import("models").Thread} */
const threadModelPatch = {
    setup() {
        super.setup(...arguments);
        /**
         * Inverse of discuss.thread, useful to efficiently check whether this thread is the one
         * currently displayed in discuss app.
         */
        this.discussAppAsThread = fields.One("DiscussApp", {
            inverse: "thread",
            /** @this {import("models").Thread} */
            onUpdate() {
                if (!this.discussAppAsThread && this.channel?.parent_channel_id) {
                    this.channel.isLocallyPinned = false;
                }
            },
        });
    },
    /** @param {boolean} pushState */
    setAsDiscussThread(pushState) {
        if (pushState === undefined) {
            pushState = !this.discussAppAsThread;
        }
        this.store.discuss.thread = this;
        if (pushState) {
            this.setActiveURL();
        }
        if (this.store.env.services.ui.isSmall && !this.store.is_welcome_page_displayed) {
            this.open({ focus: true });
        }
    },

    setActiveURL() {
        this.store.discuss.setActiveURL(`discuss.channel_${this.id}`);
    },
    /** @param {string} body */
    async askLeaveConfirmation(body) {
        await new Promise((resolve) => {
            this.store.env.services.dialog.add(ConfirmationDialog, {
                body: body,
                confirmLabel: _t("Leave Conversation"),
                confirm: resolve,
                cancel: () => {},
            });
        });
    },
};
patch(Thread.prototype, threadModelPatch);
