import { onRendered } from "@odoo/owl";

import { Discuss } from "@mail/core/common/discuss";
import { DiscussSidebar } from "@mail/core/web/discuss_sidebar";
import { MessagingMenu } from "@mail/core/web/messaging_menu";

import { ControlPanel } from "@web/search/control_panel/control_panel";
import { patch } from "@web/core/utils/patch";

Object.assign(Discuss.components, { ControlPanel, DiscussSidebar, MessagingMenu });

patch(Discuss.prototype, {
    setup() {
        super.setup();
        onRendered(() => {
            if (this.thread?.displayName) {
                this.env.config?.setDisplayName(this.thread.displayName);
            }
        });
    },
});
