import { ActionList } from "@mail/core/common/action_list";
import { useThreadActions } from "@mail/core/common/thread_actions";
import { propSignal } from "@mail/utils/common/hooks";

import { Component, computed, t } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class DiscussSidebarChannelActions extends Component {
    static template = "mail.DiscussSidebarChannelActions";
    static components = { ActionList };

    setup() {
        this.store = useService("mail.store");
        this.channel = propSignal("channel", t.instanceOf(this.store["discuss.channel"].Class));
        this.isDiscussSidebarChannelActions = true;
        this.threadActions = useThreadActions({ thread: computed(() => this.channel().thread) });
    }
}
