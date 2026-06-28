import { ActionList } from "@mail/core/common/action_list";
import { useThreadActions } from "@mail/core/common/thread_actions";

import { Component, props, types } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class DiscussSidebarChannelActions extends Component {
    static template = "mail.DiscussSidebarChannelActions";
    static components = { ActionList };

    setup() {
        this.store = useService("mail.store");
        this.props = props({
            channel: types.instanceOf(this.store["discuss.channel"].Class),
        });
        this.isDiscussSidebarChannelActions = true;
        this.threadActions = useThreadActions({ thread: () => this.channel.thread });
    }

    get channel() {
        return this.props.channel;
    }
}
