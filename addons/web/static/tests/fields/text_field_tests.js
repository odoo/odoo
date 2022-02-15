/** @odoo-module **/

import { click, triggerEvent } from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

let serverData;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        foo: {
                            string: "Foo",
                            type: "char",
                            default: "My little Foo Value",
                            searchable: true,
                            trim: true,
                        },
                        bar: { string: "Bar", type: "boolean", default: true, searchable: true },
                        txt: {
                            string: "txt",
                            type: "text",
                        },
                        int_field: {
                            string: "int_field",
                            type: "integer",
                            sortable: true,
                            searchable: true,
                        },
                        qux: { string: "Qux", type: "float", digits: [16, 1], searchable: true },
                    },
                    records: [
                        {
                            id: 1,
                            bar: true,
                            foo: "yop",
                            int_field: 10,
                            qux: 0.44444,
                            txt: "some text",
                        },
                    ],
                },
                "ir.translation": {
                    fields: {
                        lang: { type: "char" },
                        value: { type: "char" },
                        res_id: { type: "integer" },
                    },
                    records: [
                        {
                            id: 99,
                            res_id: 37,
                            value: "",
                            lang: "en_US",
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("TextField");

    QUnit.test("text fields are correctly rendered", async function (assert) {
        assert.expect(7);

        serverData.models.partner.fields.foo.type = "text";
        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="foo" />
                </form>
            `,
        });

        assert.containsOnce(form.el, ".o_field_text", "should have a text area");
        assert.strictEqual(
            form.el.querySelector(".o_field_text").textContent,
            "yop",
            "should be 'yop' in readonly"
        );

        await click(form.el, ".o_form_button_edit");
        const textarea = form.el.querySelector(".o_field_text textarea");
        assert.ok(textarea, "should have a text area");
        assert.strictEqual(textarea.value, "yop", "should still be 'yop' in edit");

        textarea.value = "hello";
        await triggerEvent(textarea, null, "change");
        assert.strictEqual(textarea.value, "hello", "should be 'hello' after first edition");

        textarea.value = "hello world";
        await triggerEvent(textarea, null, "change");

        assert.strictEqual(
            textarea.value,
            "hello world",
            "should be 'hello world' after second edition"
        );

        await click(form.el, ".o_form_button_save");

        assert.strictEqual(
            form.el.querySelector(".o_field_text").textContent,
            "hello world",
            "should be 'hello world' after save"
        );
    });

    QUnit.test("text fields in edit mode have correct height", async function (assert) {
        assert.expect(2);

        serverData.models.partner.fields.foo.type = "text";
        serverData.models.partner.records[0].foo = "f\nu\nc\nk\nm\ni\nl\ng\nr\no\nm";
        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="foo" />
                </form>
            `,
        });

        const field = form.el.querySelector(".o_field_text");
        assert.strictEqual(
            field.offsetHeight,
            field.scrollHeight,
            "text field should not have a scroll bar"
        );

        await click(form.el, ".o_form_button_edit");

        const textarea = form.el.querySelector(".o_field_text textarea");
        assert.strictEqual(
            textarea.clientHeight,
            textarea.scrollHeight - Math.abs(textarea.scrollTop),
            "textarea should not have a scroll bar"
        );
    });

    QUnit.test("text fields in edit mode, no vertical resize", async function (assert) {
        assert.expect(1);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="txt" />
                </form>
            `,
        });

        await click(form.el, ".o_form_button_edit");

        assert.strictEqual(
            window.getComputedStyle(form.el.querySelector("textarea")).resize,
            "none",
            "should not have vertical resize"
        );
    });

    QUnit.test("text fields should have correct height after onchange", async function (assert) {
        assert.expect(2);

        const damnLongText = `Lorem ipsum dolor sit amet, consectetur adipiscing elit.
            Donec est massa, gravida eget dapibus ac, eleifend eget libero.
            Suspendisse feugiat sed massa eleifend vestibulum. Sed tincidunt
            velit sed lacinia lacinia. Nunc in fermentum nunc. Vestibulum ante
            ipsum primis in faucibus orci luctus et ultrices posuere cubilia
            Curae; Nullam ut nisi a est ornare molestie non vulputate orci.
            Nunc pharetra porta semper. Mauris dictum eu nulla a pulvinar. Duis
            eleifend odio id ligula congue sollicitudin. Curabitur quis aliquet
            nunc, ut aliquet enim. Suspendisse malesuada felis non metus
            efficitur aliquet.`;

        serverData.models.partner.records[0].txt = damnLongText;
        serverData.models.partner.records[0].bar = false;
        serverData.models.partner.onchanges = {
            bar(obj) {
                obj.txt = damnLongText;
            },
        };
        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="bar" />
                    <field name="txt" attrs="{'invisible': [('bar', '=', True)]}" />
                </form>
            `,
        });

        await click(form.el, ".o_form_button_edit");

        let textarea = form.el.querySelector(".o_field_widget[name='txt'] textarea");
        const initialHeight = textarea.offsetHeight;

        textarea.value = "Short value";
        await triggerEvent(textarea, null, "change");

        assert.ok(textarea.offsetHeight < initialHeight, "Textarea height should have shrank");

        await click(form.el, ".o_field_boolean[name='bar'] input");
        await click(form.el, ".o_field_boolean[name='bar'] input");

        textarea = form.el.querySelector(".o_field_widget[name='txt'] textarea");
        assert.strictEqual(textarea.offsetHeight, initialHeight, "Textarea height should be reset");
    });

    QUnit.test("text fields in editable list have correct height", async function (assert) {
        assert.expect(2);

        serverData.models.partner.records[0].txt = "a\nb\nc\nd\ne\nf";

        const list = await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch:
                '<list editable="top">' + '<field name="foo"/>' + '<field name="txt"/>' + "</list>",
        });

        // Click to enter edit: in this test we specifically do not set
        // the focus on the textarea by clicking on another column.
        // The main goal is to test the resize is actually triggered in this
        // particular case.
        await click(list.el.querySelectorAll(".o_data_cell")[1]);
        const textarea = list.el.querySelector("textarea:first-child");

        // make sure the correct data is there
        assert.strictEqual(textarea.value, serverData.models.partner.records[0].txt);

        // make sure there is no scroll bar
        assert.strictEqual(
            textarea.clientHeight,
            textarea.scrollHeight,
            "textarea should not have a scroll bar"
        );
    });

    QUnit.test("text fields in edit mode should resize on reset", async function (assert) {
        assert.expect(1);

        serverData.models.partner.fields.foo.type = "text";

        serverData.models.partner.onchanges = {
            bar(obj) {
                obj.foo = "a\nb\nc\nd\ne\nf";
            },
        };

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="bar" />
                    <field name="foo" />
                </form>
            `,
        });

        // edit the form
        // trigger a textarea reset (through onchange) by clicking the box
        // then check there is no scroll bar
        await click(form.el, ".o_form_button_edit");
        await click(form.el, "div[name='bar'] input");

        const textarea = form.el.querySelector("textarea");
        assert.strictEqual(
            textarea.clientHeight,
            textarea.scrollHeight,
            "textarea should not have a scroll bar"
        );
    });

    QUnit.skipWOWL("text field translatable", async function (assert) {
        assert.expect(3);

        serverData.models.partner.fields.txt.translate = true;

        var multiLang = _t.database.multi_lang;
        _t.database.multi_lang = true;

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="txt"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            res_id: 1,
            mockRPC: function (route, args) {
                if (route === "/web/dataset/call_button" && args.method === "translate_fields") {
                    assert.deepEqual(
                        args.args,
                        ["partner", 1, "txt"],
                        'should call "call_button" route'
                    );
                    return Promise.resolve({
                        domain: [],
                        context: { search_default_name: "partnes,foo" },
                    });
                }
                if (route === "/web/dataset/call_kw/res.lang/get_installed") {
                    return Promise.resolve([["en_US"], ["fr_BE"]]);
                }
                return this._super.apply(this, arguments);
            },
        });
        await click(form.el, ".o_form_button_edit");
        var $button = form.el.querySelector("textarea + .o_field_translate");
        assert.strictEqual($button.length, 1, "should have a translate button");
        await testUtils.dom.click($button);
        assert.containsOnce($(document), ".modal", "there should be a translation modal");
        _t.database.multi_lang = multiLang;
    });

    QUnit.skipWOWL("text field translatable in create mode", async function (assert) {
        assert.expect(1);

        serverData.models.partner.fields.txt.translate = true;

        var multiLang = _t.database.multi_lang;
        _t.database.multi_lang = true;
        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="txt"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
        });
        var $button = form.el.querySelector("textarea + .o_field_translate");
        assert.strictEqual($button.length, 1, "should have a translate button in create mode");

        _t.database.multi_lang = multiLang;
    });

    QUnit.skipWOWL(
        "go to next line (and not the next row) when pressing enter",
        async function (assert) {
            assert.expect(4);

            serverData.models.partner.fields.foo.type = "text";
            const list = await makeView({
                type: "list",
                resModel: "partner",
                serverData,
                arch:
                    '<list editable="top">' +
                    '<field name="int_field"/>' +
                    '<field name="foo"/>' +
                    '<field name="qux"/>' +
                    "</list>",
            });

            await click(list.el.querySelector("tbody tr:first-child .o_list_text"));
            const textarea = list.el.querySelector("textarea.o_input");
            assert.containsOnce(list, textarea, "should have a text area");
            assert.strictEqual(textarea.value, "yop", 'should still be "yop" in edit');

            assert.strictEqual(
                list.el.querySelector("textarea"),
                document.activeElement,
                "text area should have the focus"
            );

            // click on enter
            await triggerEvent(textarea, null, "keydown", { key: "Enter" });
            await triggerEvent(textarea, null, "keyup", { key: "Enter" });

            assert.strictEqual(
                list.el.querySelector("textarea"),
                document.activeElement,
                "text area should still have the focus"
            );
        }
    );

    // Firefox-specific
    // Copying from <div style="white-space:pre-wrap"> does not keep line breaks
    // See https://bugzilla.mozilla.org/show_bug.cgi?id=1390115
    QUnit.test(
        "copying text fields in RO mode should preserve line breaks",
        async function (assert) {
            assert.expect(1);

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch:
                    '<form string="Partners">' +
                    "<sheet>" +
                    "<group>" +
                    '<field name="txt"/>' +
                    "</group>" +
                    "</sheet>" +
                    "</form>",
                resId: 1,
            });

            // Copying from a div tag with white-space:pre-wrap doesn't work in Firefox
            assert.strictEqual(
                form.el.querySelector('[name="txt"]').firstElementChild.tagName.toLowerCase(),
                "span",
                "the field contents should be surrounded by a span tag"
            );
        }
    );

    QUnit.test("text field rendering in list view", async function (assert) {
        assert.expect(1);

        const list = await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: '<tree><field name="txt"/></tree>',
        });

        assert.containsOnce(
            list,
            "tbody td.o_list_text",
            "should have a td with the .o_list_text class"
        );
    });

    QUnit.skipWOWL(
        "binary fields input value is empty whean clearing after uploading",
        async function (assert) {
            assert.expect(2);

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch:
                    '<form string="Partners">' +
                    '<field name="document" filename="foo"/>' +
                    '<field name="foo"/>' +
                    "</form>",
                res_id: 1,
            });

            await click(form.el, ".o_form_button_edit");

            // // We need to convert the input type since we can't programmatically set the value of a file input
            form.el.querySelector(".o_input_file").attr("type", "text").val("coucou.txt");

            assert.strictEqual(
                form.el.querySelector(".o_input_file").val(),
                "coucou.txt",
                'input value should be changed to "coucou.txt"'
            );

            await testUtils.dom.click(
                form.el.querySelector(".o_field_binary_file > .o_clear_file_button")
            );

            assert.strictEqual(
                form.el.querySelector(".o_input_file").val(),
                "",
                "input value should be empty"
            );
        }
    );

    QUnit.skipWOWL("field text in editable list view", async function (assert) {
        assert.expect(1);

        serverData.models.partner.fields.foo.type = "text";

        var list = await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: '<tree string="Phonecalls" editable="top">' + '<field name="foo"/>' + "</tree>",
        });

        await click(list.el.querySelector(".o_list_button_add"));

        assert.strictEqual(
            list.el.querySelector("textarea"),
            document.activeElement,
            "text area should have the focus"
        );
    });
});
