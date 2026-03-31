import { Store } from "@mail/../tests/mock_server/store";

import { models } from "@web/../tests/web_test_helpers";

export class MailComposeMessage extends models.ServerModel {
    _name = "mail.compose.message";
    _views = {
        "form,false": `
                <form>
                    <field name="body" widget="html_composer_message"/>
                    <footer>
                        <button name="action_send_mail" type="object" string="Send"/>
                        <button special="cancel" string="Discard"/>
                    </footer>
                </form>
            `,
    };

    action_send_mail() {
        return {
            type: "ir.actions.client",
            tag: "action_send_mail_callback",
            params: {
                record_name: "Mitchell Admin",
            },
        };
    }

    web_save(ids, values, kwargs = {}) {
        const context = kwargs.context || {};
        const messageId = context.default_message_id;
        if (!messageId) {
            return super.web_save(ids, values, kwargs);
        }
        const MailMessage = this.env["mail.message"];
        const [message] = MailMessage.browse(messageId);
        if (!message) {
            return [];
        }
        const msg_values = {};
        if (values.body !== null) {
            msg_values.body = values.body || "";
        }
        MailMessage.write([messageId], msg_values);
        this.env["bus.bus"]._sendone(
            MailMessage._bus_notification_target(messageId),
            "mail.record/insert",
            new Store().add(MailMessage.browse(messageId), "_store_message_fields").as_dict()
        );
        return [
            {
                id: messageId,
                body: values.body || "",
            },
        ];
    }
}
