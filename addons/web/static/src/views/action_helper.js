import { Component } from "@odoo/owl";

export class ActionHelper extends Component {
    static template = "web.ActionHelper";
    static props = {
        noContentHelp: { type: String, optional: true },
    };

    get showDefaultHelper() {
        return !this.props.noContentHelp;
    }
}
