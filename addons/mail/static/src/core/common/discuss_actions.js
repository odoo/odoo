import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {Object} action
 * @property {Object} action.context
 * @property {number} [action.context.active_id]
 * @property {Object} [action.params]
 * @property {number} [action.params.active_id]
 * @extends {Component<Props, Env>}
 */
export class DiscussActions extends Component {
    static components = { Dropdown, DropdownItem };
    static props = ["inline?", "dropdown?", "quick?", "group?", "other?", "pretty?", "thread?"];
    static defaultProps = { pretty: true };
    static template = "mail.DiscussActions";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.ui = useService("ui");
    }

    get inlinePretty() {
        return Boolean(this.props.inline && this.props.pretty);
    }
}
