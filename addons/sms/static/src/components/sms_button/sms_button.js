/** @odoo-module **/

import { useActionLinks } from "@web/views/helpers/view_hook";

const { Component } = owl;

export class SendSMSButton extends Component {
    setup() {
        // This helper might be useful to trigger doAction correctly
        // and show the compose sms window
        useActionLinks({
            actionContext: {
                ...this.props.record.context,
                default_res_id: this.props.record.resId,
                default_res_model: this.props.record.resModel,
                default_composition_mode: "comment",
                default_number_field_name: "phone",
            },
        });
    }
};
SendSMSButton.template = "sms.SendSMSButton";
