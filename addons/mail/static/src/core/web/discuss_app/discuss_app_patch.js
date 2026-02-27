import { useEffect } from "@odoo/owl";

import { Discuss } from "@mail/core/public_web/discuss_app/discuss_app";
import { MessagingMenu } from "@mail/core/public_web/messaging_menu";

import { ControlPanel } from "@web/search/control_panel/control_panel";
import { patch } from "@web/core/utils/patch";

Object.assign(Discuss.components, { ControlPanel, MessagingMenu });

patch(Discuss.prototype, {
    setup() {
        super.setup();
        useEffect(
            (threadName) => {
                if (threadName) {
                    this.env.config?.setDisplayName(threadName);
                }
            },
            () => [this.thread?.displayName]
        );
    },
});
