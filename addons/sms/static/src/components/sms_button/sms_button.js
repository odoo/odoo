/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";

const { Component } = owl;

export class SendSMSButton extends Component {
    setup() {
        this.action = useService("action");
        this.title = this.env._t("Send SMS Text Message");
    }
    onClick() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: this.title,
            res_id: this.props.record.resId,
            res_model: "sms.composer",
            target: "new",
            views: [[false, "form"]],
        });
    }
};
SendSMSButton.template = "sms.SendSMSButton";
