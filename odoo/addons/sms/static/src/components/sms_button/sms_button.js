/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Component, status } from "@odoo/owl";

export class SendSMSButton extends Component {
    setup() {
        this.action = useService("action");
        this.user = useService("user");
        this.title = _t("Send SMS Text Message");
    }
    get phoneHref() {
        return "sms:" + this.props.record.data[this.props.name].replace(/\s+/g, "");
    }
    async onClick() {
        await this.props.record.save();
        this.action.doAction(
            {
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
                    default_composition_mode: "comment",
                },
            },
            {
                onClose: () => {
                    if (status(this) === "destroyed") {
                        return;
                    }
                    this.props.record.load();
                },
            }
        );
    }
}
SendSMSButton.template = "sms.SendSMSButton";
SendSMSButton.props = ["*"];
