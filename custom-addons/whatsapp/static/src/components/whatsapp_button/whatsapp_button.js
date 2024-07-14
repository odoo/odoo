/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

import { Component } from "@odoo/owl";

export class SendWhatsAppButton extends Component {
    static template = "whatsapp.SendWhatsAppButton";
    static props = ["*"];

    setup() {
        this.action = useService("action");
        this.user = useService("user");
        this.title = _t("Send WhatsApp Message");
    }

    async onClick() {
        await this.props.record.save();
        this.action.doAction(
            {
                type: "ir.actions.act_window",
                target: "new",
                name: this.title,
                res_model: "whatsapp.composer",
                views: [[false, "form"]],
                context: {
                    ...this.user.context,
                    active_model: this.props.record.resModel,
                    active_id: this.props.record.resId,
                    default_phone: this.props.record.data[this.props.name],
                },
            },
            {
                onClose: () => {
                    this.props.record.load();
                    this.props.record.model.notify();
                },
            }
        );
    }
}
