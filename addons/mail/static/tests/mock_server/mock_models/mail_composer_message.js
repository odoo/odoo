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
}
