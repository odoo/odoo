/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

const { Component } = owl;

export class SendSMSButton extends Component {
    setup() {
        this.action = useService("action");
        this.title = _lt('Send SMS Text Message');
    }
    onClick() {
        //TODO Must be checked
        const action = {
            type: "ir.actions.act_window",
            name: this.title,
            res_id: this.props.record.resId,
            res_model: "sms.composer",
            target: "new",
            views: [[false, "form"]],
        };
        this.action.doAction(action);
    }
};
SendSMSButton.template = "sms.SendSMSButton";
