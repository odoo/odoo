/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";

const { Component } = owl;

export class SendSMSButton extends Component {
    setup() {
        this.action = useService("action");
        this.user = useService("user");
        this.title = this.env._t("Send SMS Text Message");
    }
    async onClick() {
        await this.props.record.save();
        this.action.doAction({
            type: "ir.actions.act_window",
            target: "new",
            name: this.title,
            res_model: "sms.composer",
            views: [[false, "form"]],
            context: {
                ...this.user.context,
                default_res_model: this.props.record.resModel,
                default_res_id: this.props.record.resId,
                default_number_field_name: this.props.name,
                default_composition_mode: 'comment',
            }
        }, {
            onClose: () => {
                this.props.record.model.load({ resId: this.props.record.resId });
            },
        });
    }
};
SendSMSButton.template = "sms.SendSMSButton";
