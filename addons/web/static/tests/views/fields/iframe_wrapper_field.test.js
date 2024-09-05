import { expect, test } from "@odoo/hoot";
import { click, edit, queryFirst } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class Report extends models.Model {
    int_field = fields.Integer();
    html_field = fields.Html();

    _records = [
        {
            id: 1,
            html_field: /* html */ `
                <html>
                    <head>
                        <style>
                            body { color : rgb(255, 0, 0); }
                        </style>
                    </head>
                    <body>
                        <div class="nice_div"><p>Some content</p></div>
                    </body>
                </html>
            `,
        },
    ];
}

defineModels([Report]);

test("IframeWrapperField in form view with onchange", async () => {
    Report._onChanges.int_field = (record) => {
        record.html_field = record.html_field.replace("Some content", "New content");
    };
    await mountView({
        type: "form",
        resModel: "report",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="int_field"/>
                <field name="html_field" widget="iframe_wrapper"/>
            </form>
        `,
    });

    expect("iframe:iframe .nice_div:first").toHaveInnerHTML("<p>Some content</p>");
    expect("iframe:iframe .nice_div p:first").toHaveStyle({
        color: "rgb(255, 0, 0)",
    });
    await click(".o_field_widget[name=int_field] input");
    await edit(264, { confirm: "enter" });
    await animationFrame();
    expect(queryFirst("iframe:iframe .nice_div")).toHaveInnerHTML("<p>New content</p>");
});
