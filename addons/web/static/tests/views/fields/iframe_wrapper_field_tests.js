/** @odoo-module **/

import { editInput, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                report: {
                    fields: {
                        int_field: { string: "Int Field", type: "integer" },
                        html_field: { string: "Content of report", type: "html" },
                    },
                    records: [
                        {
                            id: 1,
                            html_field: `
                                <html>
                                    <head>
                                        <style>
                                            body { color : rgb(255, 0, 0); }
                                        </style>
                                    <head>
                                    <body>
                                        <div class="nice_div"><p>Some content</p></div>
                                    </body>
                                </html>`,
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("IframeWrapperField");

    QUnit.test("IframeWrapperField in form view", async function (assert) {
        await makeView({
            type: "form",
            resModel: "report",
            serverData,
            resId: 1,
            arch: `
                <form>
                    <field name="html_field" widget="iframe_wrapper"/>
                </form>`,
        });

        const iframeDoc = target.querySelector("iframe").contentDocument;
        assert.strictEqual(iframeDoc.querySelector(".nice_div").innerHTML, "<p>Some content</p>");
        assert.strictEqual($(iframeDoc).find(".nice_div p").css("color"), "rgb(255, 0, 0)");
    });

    QUnit.test("IframeWrapperField in form view with onchange", async function (assert) {
        serverData.models.report.onchanges = {
            int_field(record) {
                record.html_field = record.html_field.replace("Some content", "New content");
            },
        };
        await makeView({
            type: "form",
            resModel: "report",
            serverData,
            resId: 1,
            arch: `
                <form>
                    <field name="int_field"/>
                    <field name="html_field" widget="iframe_wrapper"/>
                </form>`,
        });

        const iframeDoc = target.querySelector("iframe").contentDocument;
        assert.strictEqual(iframeDoc.querySelector(".nice_div").innerHTML, "<p>Some content</p>");
        assert.strictEqual($(iframeDoc).find(".nice_div p").css("color"), "rgb(255, 0, 0)");

        await editInput(target, ".o_field_widget[name=int_field] input", 264);
        assert.strictEqual(iframeDoc.querySelector(".nice_div").innerHTML, "<p>New content</p>");
    });
});
