import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component } from "@odoo/owl";

/**
 * Will be removed in master
 * @deprecated
 */
export class MailComposerShowBccButton extends Component {
    static template = "mail.MailComposerShowBccButton";
    static components = {};
    static props = { ...standardFieldProps };

    async onBtnClick() {
        await this.props.record.update({
            [this.props.name]: !this.props.record.data[this.props.name],
        });
    }
}

export const mailComposerShowBccButton = {
    component: MailComposerShowBccButton,
};

registry.category("fields").add("mail_composer_show_bcc_button", mailComposerShowBccButton);
