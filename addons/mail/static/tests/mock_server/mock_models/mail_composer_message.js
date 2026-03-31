import { Store } from "@mail/../tests/mock_server/store";

import { models } from "@web/../tests/web_test_helpers";

export class MailComposeMessage extends models.ServerModel {
    _name = "mail.compose.message";
    _views = {
        "form,false": `
                <form>
                    <field name="body" widget="html_composer_message"/>
                    <footer>
                        <button name="action_send_mail" type="object" string="Send"
                            invisible="context.get('default_message_id')"/>
                        <button name="action_update_message" type="object" string="Save"
                            invisible="not context.get('default_message_id')"/>
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

    action_update_message(ids, kwargs = {}) {
        const MailMessage = this.env["mail.message"];
        const messageId = kwargs.context?.default_message_id;
        const [composer] = this.browse(ids);
        MailMessage.write([messageId], { body: composer.body || "" });
        this.env["bus.bus"]._sendone(
            MailMessage._bus_notification_target(messageId),
            "mail.record/insert",
            new Store().add(MailMessage.browse(messageId), "_store_message_fields").as_dict()
        );
        return { type: "ir.actions.act_window_close" };
    }
}
