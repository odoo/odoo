import { useThreadActions } from "@mail/core/common/thread_actions";

import { Component } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
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
    static components = { DropdownItem };

    setup() {
        this.store = useService("mail.store");
        this.threadActions = useThreadActions();
    }

    get thread() {
        return this.props.thread;
    }

    open(action) {
        action.open();
    }
}
