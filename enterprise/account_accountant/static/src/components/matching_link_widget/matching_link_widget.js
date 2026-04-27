/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";

class MatchingLink extends Component {
    static props = { ...standardFieldProps };
    static template = "account_accountant.MatchingLink";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
    }

    async reconcile() {
        this.action.doAction("account_accountant.action_move_line_posted_unreconciled", {
            additionalContext: {
                search_default_partner_id: this.props.record.data.partner_id[0],
                search_default_account_id: this.props.record.data.account_id[0],
            },
        });
    }

    async viewMatch() {
        const action = await this.orm.call("account.move.line", "open_reconcile_view", [this.props.record.resId], {});
        this.action.doAction(action, { additionalContext: { is_matched_view: true } });
    }

    get colorCode() {
        const matchValue = this.props.record.data[this.props.name];
        const matchColorValue = matchValue.replace('P', '');
        if (matchColorValue === '*') {
            // reserve color code 0 for multi partial matches
            return 0;
        } else {
            // there is 12 available color palette for 'o_tag_color_*'
            // since the color code 0 has been reserved by 'P*', we can only use color codes between 1 and 11
            return parseInt(matchColorValue) % 11 + 1;
        }
    }
}

registry.category("fields").add("matching_link_widget", {
    component: MatchingLink,
});
