/** @odoo-module **/

import { dialogService } from "@web/core/dialog/dialog_service";
import { registry } from "@web/core/registry";
import { makeFakeLocalizationService, makeFakeUserService } from "../helpers/mock_services";
import { click, makeDeferred, nextTick, triggerEvent, triggerEvents } from "../helpers/utils";
import {
    setupControlPanelFavoriteMenuRegistry,
    setupControlPanelServiceRegistry,
} from "../search/helpers";
import { makeView } from "../views/helpers";

const serviceRegistry = registry.category("services");

let serverData;

function hasGroup(group) {
    return group === "base.group_allow_export";
}

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        date: { string: "A date", type: "date", searchable: true },
                        datetime: { string: "A datetime", type: "datetime", searchable: true },
                        display_name: { string: "Displayed name", type: "char", searchable: true },
                        foo: {
                            string: "Foo",
                            type: "char",
                            default: "My little Foo Value",
                            searchable: true,
                            trim: true,
                        },
                        bar: { string: "Bar", type: "boolean", default: true, searchable: true },
                        empty_string: {
                            string: "Empty string",
                            type: "char",
                            default: false,
                            searchable: true,
                            trim: true,
                        },
                        txt: {
                            string: "txt",
                            type: "text",
                            default: "My little txt Value\nHo-ho-hoooo Merry Christmas",
                        },
                        int_field: {
                            string: "int_field",
                            type: "integer",
                            sortable: true,
                            searchable: true,
                        },
                        qux: { string: "Qux", type: "float", digits: [16, 1], searchable: true },
                        p: {
                            string: "one2many field",
                            type: "one2many",
                            relation: "partner",
                            searchable: true,
                        },
                        trululu: {
                            string: "Trululu",
                            type: "many2one",
                            relation: "partner",
                            searchable: true,
                        },
                        timmy: {
                            string: "pokemon",
                            type: "many2many",
                            relation: "partner_type",
                            searchable: true,
                        },
                        product_id: {
                            string: "Product",
                            type: "many2one",
                            relation: "product",
                            searchable: true,
                        },
                        sequence: { type: "integer", string: "Sequence", searchable: true },
                        currency_id: {
                            string: "Currency",
                            type: "many2one",
                            relation: "currency",
                            searchable: true,
                        },
                        selection: {
                            string: "Selection",
                            type: "selection",
                            searchable: true,
                            selection: [
                                ["normal", "Normal"],
                                ["blocked", "Blocked"],
                                ["done", "Done"],
                            ],
                        },
                        document: { string: "Binary", type: "binary" },
                        hex_color: { string: "hexadecimal color", type: "char" },
                    },
                    records: [
                        {
                            id: 1,
                            date: "2017-02-03",
                            datetime: "2017-02-08 10:00:00",
                            display_name: "first record",
                            bar: true,
                            foo: "yop",
                            int_field: 10,
                            qux: 0.44444,
                            p: [],
                            timmy: [],
                            trululu: 4,
                            selection: "blocked",
                            document: "coucou==\n",
                            hex_color: "#ff0000",
                        },
                        {
                            id: 2,
                            display_name: "second record",
                            bar: true,
                            foo: "blip",
                            int_field: 0,
                            qux: 0,
                            p: [],
                            timmy: [],
                            trululu: 1,
                            sequence: 4,
                            currency_id: 2,
                            selection: "normal",
                        },
                        {
                            id: 4,
                            display_name: "aaa",
                            foo: "abc",
                            sequence: 9,
                            int_field: false,
                            qux: false,
                            selection: "done",
                        },
                        { id: 3, bar: true, foo: "gnap", int_field: 80, qux: -3.89859 },
                        { id: 5, bar: false, foo: "blop", int_field: -4, qux: 9.1, currency_id: 1 },
                    ],
                    onchanges: {},
                },
                product: {
                    fields: {
                        name: { string: "Product Name", type: "char", searchable: true },
                    },
                    records: [
                        {
                            id: 37,
                            display_name: "xphone",
                        },
                        {
                            id: 41,
                            display_name: "xpad",
                        },
                    ],
                },
                partner_type: {
                    fields: {
                        name: { string: "Partner Type", type: "char", searchable: true },
                        color: { string: "Color index", type: "integer", searchable: true },
                    },
                    records: [
                        { id: 12, display_name: "gold", color: 2 },
                        { id: 14, display_name: "silver", color: 5 },
                    ],
                },
                currency: {
                    fields: {
                        digits: { string: "Digits" },
                        symbol: { string: "Currency Sumbol", type: "char", searchable: true },
                        position: { string: "Currency Position", type: "char", searchable: true },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "$",
                            symbol: "$",
                            position: "before",
                        },
                        {
                            id: 2,
                            display_name: "€",
                            symbol: "€",
                            position: "after",
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

        setupControlPanelFavoriteMenuRegistry();
        setupControlPanelServiceRegistry();
        serviceRegistry.add("dialog", dialogService);
        serviceRegistry.add("user", makeFakeUserService(hasGroup), { force: true });
    });

    QUnit.module("TextField");

    QUnit.test("text fields are correctly rendered", async function (assert) {
        assert.expect(7);

        serverData.models.partner.fields.foo.type = "text";
        var form = await makeView({
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

        const textarea = form.el.querySelector("textarea.o_field_text");
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

    QUnit.skip("text fields in edit mode have correct height", async function (assert) {
        assert.expect(2);

        serverData.models.partner.fields.foo.type = "text";
        serverData.models.partner.records[0].foo = "f\nu\nc\nk\nm\ni\nl\ng\nr\no\nm";
        var form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form string="Partners">' + '<field name="foo"/>' + "</form>",
            res_id: 1,
        });

        var $field = form.$(".o_field_text");

        assert.strictEqual(
            $field[0].offsetHeight,
            $field[0].scrollHeight,
            "text field should not have a scroll bar"
        );

        await testUtils.form.clickEdit(form);

        var $textarea = form.$("textarea:first");

        // the difference is to take small calculation errors into account
        assert.strictEqual(
            $textarea[0].clientHeight,
            $textarea[0].scrollHeight,
            "textarea should not have a scroll bar"
        );
        form.destroy();
    });

    QUnit.skip("text fields in edit mode, no vertical resize", async function (assert) {
        assert.expect(1);

        var form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form string="Partners">' + '<field name="txt"/>' + "</form>",
            res_id: 1,
        });

        await testUtils.form.clickEdit(form);

        var $textarea = form.$("textarea:first");

        assert.strictEqual($textarea.css("resize"), "none", "should not have vertical resize");

        form.destroy();
    });

    QUnit.skip("text fields should have correct height after onchange", async function (assert) {
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
            bar: function (obj) {
                obj.txt = damnLongText;
            },
        };
        const form = await makeView({
            arch: `
                <form string="Partners">
                    <field name="bar"/>
                    <field name="txt" attrs="{'invisible': [('bar', '=', True)]}"/>
                </form>`,
            serverData,
            resModel: "partner",
            res_id: 1,
            type: "form",
            viewOptions: { mode: "edit" },
        });

        const textarea = form.el.querySelector('textarea[name="txt"]');
        const initialHeight = textarea.offsetHeight;

        await testUtils.fields.editInput($(textarea), "Short value");

        assert.ok(textarea.offsetHeight < initialHeight, "Textarea height should have shrank");

        await testUtils.dom.click(form.$('.o_field_boolean[name="bar"] input'));
        await testUtils.dom.click(form.$('.o_field_boolean[name="bar"] input'));

        assert.strictEqual(textarea.offsetHeight, initialHeight, "Textarea height should be reset");

        form.destroy();
    });

    QUnit.skip("text fields in editable list have correct height", async function (assert) {
        assert.expect(2);

        serverData.models.partner.records[0].txt = "a\nb\nc\nd\ne\nf";

        var list = await makeView({
            View: ListView,
            resModel: "partner",
            serverData,
            arch:
                '<list editable="top">' + '<field name="foo"/>' + '<field name="txt"/>' + "</list>",
        });

        // Click to enter edit: in this test we specifically do not set
        // the focus on the textarea by clicking on another column.
        // The main goal is to test the resize is actually triggered in this
        // particular case.
        await testUtils.dom.click(list.$(".o_data_cell:first"));
        var $textarea = list.$("textarea:first");

        // make sure the correct data is there
        assert.strictEqual($textarea.val(), serverData.models.partner.records[0].txt);

        // make sure there is no scroll bar
        assert.strictEqual(
            $textarea[0].clientHeight,
            $textarea[0].scrollHeight,
            "textarea should not have a scroll bar"
        );

        list.destroy();
    });

    QUnit.skip("text fields in edit mode should resize on reset", async function (assert) {
        assert.expect(1);

        serverData.models.partner.fields.foo.type = "text";

        serverData.models.partner.onchanges = {
            bar: function (obj) {
                obj.foo = "a\nb\nc\nd\ne\nf";
            },
        };

        var form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch:
                '<form string="Partners">' +
                '<field name="bar"/>' +
                '<field name="foo"/>' +
                "</form>",
            res_id: 1,
        });

        // edit the form
        // trigger a textarea reset (through onchange) by clicking the box
        // then check there is no scroll bar
        await testUtils.form.clickEdit(form);

        await testUtils.dom.click(form.$('div[name="bar"] input'));

        var $textarea = form.$("textarea:first");
        assert.strictEqual(
            $textarea.innerHeight(),
            $textarea[0].scrollHeight,
            "textarea should not have a scroll bar"
        );

        form.destroy();
    });

    QUnit.skip("text field translatable", async function (assert) {
        assert.expect(3);

        serverData.models.partner.fields.txt.translate = true;

        var multiLang = _t.database.multi_lang;
        _t.database.multi_lang = true;

        var form = await makeView({
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
        await testUtils.form.clickEdit(form);
        var $button = form.$("textarea + .o_field_translate");
        assert.strictEqual($button.length, 1, "should have a translate button");
        await testUtils.dom.click($button);
        assert.containsOnce($(document), ".modal", "there should be a translation modal");
        form.destroy();
        _t.database.multi_lang = multiLang;
    });

    QUnit.skip("text field translatable in create mode", async function (assert) {
        assert.expect(1);

        serverData.models.partner.fields.txt.translate = true;

        var multiLang = _t.database.multi_lang;
        _t.database.multi_lang = true;
        var form = await makeView({
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
        var $button = form.$("textarea + .o_field_translate");
        assert.strictEqual($button.length, 1, "should have a translate button in create mode");
        form.destroy();

        _t.database.multi_lang = multiLang;
    });

    QUnit.skip(
        "go to next line (and not the next row) when pressing enter",
        async function (assert) {
            assert.expect(4);

            serverData.models.partner.fields.foo.type = "text";
            var list = await makeView({
                View: ListView,
                resModel: "partner",
                serverData,
                arch:
                    '<list editable="top">' +
                    '<field name="int_field"/>' +
                    '<field name="foo"/>' +
                    '<field name="qux"/>' +
                    "</list>",
            });

            await testUtils.dom.click(list.$("tbody tr:first .o_list_text"));
            var $textarea = list.$("textarea.o_field_text");
            assert.strictEqual($textarea.length, 1, "should have a text area");
            assert.strictEqual($textarea.val(), "yop", 'should still be "yop" in edit');

            assert.strictEqual(
                list.$("textarea").get(0),
                document.activeElement,
                "text area should have the focus"
            );

            // click on enter
            list.$("textarea")
                .trigger({ type: "keydown", which: $.ui.keyCode.ENTER })
                .trigger({ type: "keyup", which: $.ui.keyCode.ENTER });

            assert.strictEqual(
                list.$("textarea").first().get(0),
                document.activeElement,
                "text area should still have the focus"
            );

            list.destroy();
        }
    );

    // Firefox-specific
    // Copying from <div style="white-space:pre-wrap"> does not keep line breaks
    // See https://bugzilla.mozilla.org/show_bug.cgi?id=1390115
    QUnit.skip(
        "copying text fields in RO mode should preserve line breaks",
        async function (assert) {
            assert.expect(1);

            var form = await makeView({
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
            });

            // Copying from a div tag with white-space:pre-wrap doesn't work in Firefox
            assert.strictEqual(
                form.$('[name="txt"]').prop("tagName").toLowerCase(),
                "span",
                "the field contents should be surrounded by a span tag"
            );

            form.destroy();
        }
    );

    QUnit.skip("text field rendering in list view", async function (assert) {
        assert.expect(1);

        var data = {
            foo: {
                fields: { foo: { string: "F", type: "text" } },
                records: [{ id: 1, foo: "some text" }],
            },
        };
        var list = await makeView({
            View: ListView,
            model: "foo",
            data: data,
            arch: '<tree><field name="foo"/></tree>',
        });

        assert.strictEqual(
            list.$("tbody td.o_list_text:contains(some text)").length,
            1,
            "should have a td with the .o_list_text class"
        );
        list.destroy();
    });

    QUnit.skip(
        "binary fields input value is empty whean clearing after uploading",
        async function (assert) {
            assert.expect(2);

            var form = await makeView({
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

            await testUtils.form.clickEdit(form);

            // // We need to convert the input type since we can't programmatically set the value of a file input
            form.$(".o_input_file").attr("type", "text").val("coucou.txt");

            assert.strictEqual(
                form.$(".o_input_file").val(),
                "coucou.txt",
                'input value should be changed to "coucou.txt"'
            );

            await testUtils.dom.click(form.$(".o_field_binary_file > .o_clear_file_button"));

            assert.strictEqual(form.$(".o_input_file").val(), "", "input value should be empty");

            form.destroy();
        }
    );

    QUnit.skip("field text in editable list view", async function (assert) {
        assert.expect(1);

        serverData.models.partner.fields.foo.type = "text";

        var list = await makeView({
            View: ListView,
            resModel: "partner",
            serverData,
            arch: '<tree string="Phonecalls" editable="top">' + '<field name="foo"/>' + "</tree>",
        });

        await testUtils.dom.click(list.$buttons.find(".o_list_button_add"));

        assert.strictEqual(
            list.$("textarea").first().get(0),
            document.activeElement,
            "text area should have the focus"
        );
        list.destroy();
    });
});
