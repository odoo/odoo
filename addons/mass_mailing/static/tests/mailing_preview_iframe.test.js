import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test, waitFor } from "@odoo/hoot";
import {
    contains,
    defineModels,
    fields,
    getService,
    models,
    mountWithCleanup,
} from "@web/../tests/web_test_helpers";
import { WebClient } from "@web/webclient/webclient";

class MailingMailingTest extends models.Model {
    _name = "mailing.mailing.test";

    subject = fields.Char();
    email_from = fields.Char();
    body_html = fields.Html();
    preview_record_ref = fields.Reference({ selection: [["res.partner", "Contact"]] });

    _records = [
        {
            id: 1,
            subject: "Hello",
            email_from: "admin@example.com",
            body_html: "<p>Hello world</p>",
        },
    ];
    _views = {
        form: /* xml */ `
            <form js_class="mailing_preview_form_view">
                <header>
                    <widget name="mailing_preview_display_mode_toggle"/>
                </header>
                <sheet>
                    <field name="subject"/>
                    <field name="email_from"/>
                    <field name="preview_record_ref" invisible="1"/>
                    <field name="body_html" widget="mailing_preview_iframe"/>
                </sheet>
            </form>
        `,
    };
}

defineModels([MailingMailingTest]);
defineMailModels();

test.tags("desktop");
test("mobile preview flags the dialog it is displayed in", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        type: "ir.actions.act_window",
        res_model: "mailing.mailing.test",
        res_id: 1,
        views: [[false, "form"]],
        target: "new",
    });
    await waitFor(".o_dialog .o_mass_mailing_iframe_wrapper");
    expect(".o_dialog .modal-dialog").not.toHaveClass("o_mass_mailing_preview_transparent_dialog");

    await contains(".o_dialog [title='Mobile Preview']").click();
    expect(".o_dialog .o_mass_mailing_preview_container").toHaveClass("o_is_mobile");
    expect(".o_dialog .modal-dialog").toHaveClass("o_mass_mailing_preview_transparent_dialog");

    await contains(".o_dialog .o_is_mobile_header [title='Desktop Preview']").click();
    expect(".o_dialog .o_mass_mailing_preview_container").not.toHaveClass("o_is_mobile");
    expect(".o_dialog .modal-dialog").not.toHaveClass("o_mass_mailing_preview_transparent_dialog");
});
