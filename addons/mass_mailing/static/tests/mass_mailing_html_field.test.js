import { mailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class Mailing extends models.Model {
    _name = "mailing.mailing";

    name = fields.Char();
    body_html = fields.Html();
    body_arch = fields.Html();

    _records = [
        {
            id: 1,
            name: "first record",
            body_html:
                "<div class='field_body' style='background-color: red;'><p>code to edit</p></div>",
            body_arch: "<div class='field_body'><p>code to edit</p></div>",
        },
    ];
}

defineModels({ ...mailModels, Mailing });

// todo: need fix hoot
test.skip("save arch and html", async () => {
    await mountView({
        type: "form",
        resModel: "mailing.mailing",
        resId: 1,
        arch: `
            <form>
                <field name="body_html" class="oe_read_only" options="{'cssReadonly': 'template.assets'}" />
                <field name="body_arch" class="oe_edit_only" widget="mass_mailing_html"
                    options="{
                            'snippets': 'web_editor.snippets',
                            'cssEdit': 'template.assets',
                            'inline-field': 'body_html'
                    }"
                />
            </form>`,
    });

    expect('.o_field_widget[name="body_html"]').not.toBeDisplayed();
    expect('.o_field_widget[name="body_arch"]').toBeDisplayed();
});
