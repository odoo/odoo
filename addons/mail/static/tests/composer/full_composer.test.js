import {
    contains,
    defineMailModels,
    mailModels,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { getService } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

// use a form view close to the real one: it notably defines the js_class
// responsible for the autofocus of the editor
mailModels.MailComposeMessage._views = {
    "form,false": `
        <form js_class="mail_composer_form" class="o_mail_composer_form">
            <field name="model" invisible="1"/>
            <field name="res_ids" invisible="1"/>
            <field name="subtype_is_log" invisible="1"/>
            <field name="partner_ids" widget="many2many_tags_email" invisible="1"/>
            <field name="partner_cc_ids" widget="many2many_tags_email" invisible="1"/>
            <field name="body" widget="html_composer_message"/>
            <footer>
                <button name="action_send_mail" type="object" string="Send"/>
                <button special="cancel" string="Discard"/>
            </footer>
        </form>`,
};

test("composer wizard dialog is closed when pressing Escape", async () => {
    // flow of the "Send by Email" buttons, which open the composer wizard in a
    // dialog
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John Jane", email: "john@jane.be" });
    const composerId = pyEnv["mail.compose.message"].create({
        body: "<p>Hello</p>",
        model: "res.partner",
        res_ids: JSON.stringify([partnerId]),
    });
    await start();
    getService("action").doAction({
        type: "ir.actions.act_window",
        res_model: "mail.compose.message",
        res_id: composerId,
        views: [[false, "form"]],
        target: "new",
    });
    await contains(".o_dialog .o_mail_composer_form");
    // the editor is focused when the composer opens: the dialog must be closed
    // even though the hotkey is pressed inside an editable element
    await contains(".o_dialog .odoo-editor-editable:focus");
    await press("Escape");
    await contains(".o_dialog", { count: 0 });
});
