import { DiscussActions } from "@mail/core/common/discuss_actions";
import { useThreadActions } from "@mail/core/common/thread_actions";

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
/**
 * @typedef {Object} Props
 * @property {import("@mail/core/common/thread_model").Thread} thread
 * @property {function} [close]
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebarChannelActions extends Component {
    static template = "mail.DiscussSidebarChannelActions";
    static props = ["thread"];
    static components = { DiscussActions };

    setup() {
        this.store = useService("mail.store");
        this.threadActions = useThreadActions();
    }

    get thread() {
        return this.props.thread;
    }
}
