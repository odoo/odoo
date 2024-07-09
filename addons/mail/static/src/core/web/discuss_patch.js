import { onRendered, useEffect } from "@odoo/owl";

import { Discuss } from "@mail/core/public_web/discuss";
import { DiscussSidebar } from "@mail/core/web/discuss_sidebar";
import { MessagingMenu } from "@mail/core/web/messaging_menu";

import { ControlPanel } from "@web/search/control_panel/control_panel";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

Object.assign(Discuss.components, { ControlPanel, DiscussSidebar, MessagingMenu });

patch(Discuss.prototype, {
    setup() {
        super.setup();
        this.prevInboxCounter = this.store.inbox.counter;
        onRendered(() => {
            if (this.thread?.displayName) {
                this.env.config?.setDisplayName(this.thread.displayName);
            }
        });
        useEffect(
            () => {
                if (
                    this.thread?.id === "inbox" &&
                    this.prevInboxCounter !== this.store.inbox.counter &&
                    this.store.inbox.counter === 0
                ) {
                    this.effect.add({
                        message: _t("Congratulations, your inbox is empty!"),
                        type: "rainbow_man",
                        fadeout: "fast",
                    });
                }
                this.prevInboxCounter = this.store.inbox.counter;
            },
            () => [this.store.inbox.counter]
        );
    },
});
