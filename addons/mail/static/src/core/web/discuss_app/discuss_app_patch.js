import { useLayoutEffect } from "@web/owl2/utils";

import { Discuss } from "@mail/core/public_web/discuss_app/discuss_app";
import { MessagingMenu } from "@mail/core/public_web/messaging_menu";

import { ControlPanel } from "@web/search/control_panel/control_panel";
import { patch } from "@web/core/utils/patch";

Object.assign(Discuss.components, { ControlPanel, MessagingMenu });

patch(Discuss.prototype, {
    setup() {
        super.setup();
        useLayoutEffect(
            (threadName) => {
                if (threadName) {
                    this.env.config?.setDisplayName(threadName);
                }
            },
            () => [this.thread?.displayName]
        );
    },
});
