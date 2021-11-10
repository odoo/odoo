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

    QUnit.module("UrlField");

    QUnit.skip("UrlField in form view", async function (assert) {
        assert.expect(10);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="foo" widget="url"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            res_id: 1,
        });

        assert.containsOnce(
            form,
            "div.o_form_uri.o_field_widget.o_text_overflow.o_field_url > a",
            "should have a anchor with correct classes"
        );
        assert.hasAttrValue(
            form.$("div.o_form_uri.o_field_widget.o_text_overflow.o_field_url > a"),
            "href",
            "http://yop",
            "should have proper href link"
        );
        assert.hasAttrValue(
            form.$("div.o_form_uri.o_field_widget.o_text_overflow.o_field_url > a"),
            "target",
            "_blank",
            "should have target attribute set to _blank"
        );
        assert.strictEqual(
            form.$("div.o_form_uri.o_field_widget.o_text_overflow.o_field_url > a").text(),
            "yop",
            "the value should be displayed properly"
        );

        // switch to edit mode and check the result
        await testUtils.form.clickEdit(form);
        assert.containsOnce(
            form,
            'input[type="text"].o_field_widget',
            "should have an input for the char field"
        );
        assert.strictEqual(
            form.$('input[type="text"].o_field_widget').val(),
            "yop",
            "input should contain field value in edit mode"
        );

        // change value in edit mode
        testUtils.fields.editInput(form.$('input[type="text"].o_field_widget'), "limbo");

        // save
        await testUtils.form.clickSave(form);
        assert.containsOnce(
            form,
            "div.o_form_uri.o_field_widget.o_text_overflow.o_field_url > a",
            "should still have a anchor with correct classes"
        );
        assert.hasAttrValue(
            form.$("div.o_form_uri.o_field_widget.o_text_overflow.o_field_url > a"),
            "href",
            "http://limbo",
            "should have proper new href link"
        );
        assert.strictEqual(
            form.$("div.o_form_uri.o_field_widget.o_text_overflow.o_field_url > a").text(),
            "limbo",
            "the new value should be displayed"
        );

        await testUtils.form.clickEdit(form);
        testUtils.fields.editInput(form.$('input[type="text"].o_field_widget'), "/web/limbo");

        await testUtils.form.clickSave(form);
        assert.hasAttrValue(
            form.$("div.o_form_uri.o_field_widget.o_text_overflow.o_field_url > a"),
            "href",
            "/web/limbo",
            "should'nt have change link"
        );

        form.destroy();
    });

    QUnit.skip("UrlField takes text from proper attribute", async function (assert) {
        assert.expect(1);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                '<field name="foo" widget="url" text="kebeclibre"/>' +
                "</form>",
            res_id: 1,
        });

        assert.strictEqual(
            form.$('div[name="foo"].o_field_url > a').text(),
            "kebeclibre",
            "url text should come from the text attribute"
        );
        form.destroy();
    });

    QUnit.skip("UrlField: href attribute and website_path option", async function (assert) {
        assert.expect(4);

        this.data.partner.fields.url1 = { string: "Url 1", type: "char", default: "www.url1.com" };
        this.data.partner.fields.url2 = { string: "Url 2", type: "char", default: "www.url2.com" };
        this.data.partner.fields.url3 = {
            string: "Url 3",
            type: "char",
            default: "http://www.url3.com",
        };
        this.data.partner.fields.url4 = {
            string: "Url 4",
            type: "char",
            default: "https://url4.com",
        };

        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: `
                <form>
                    <field name="url1" widget="url"/>
                    <field name="url2" widget="url" options="{'website_path': True}"/>
                    <field name="url3" widget="url"/>
                    <field name="url4" widget="url"/>
                </form>`,
            res_id: 1,
        });

        assert.strictEqual(
            form.$('div[name="url1"].o_field_url > a').attr("href"),
            "http://www.url1.com"
        );
        assert.strictEqual(form.$('div[name="url2"].o_field_url > a').attr("href"), "www.url2.com");
        assert.strictEqual(
            form.$('div[name="url3"].o_field_url > a').attr("href"),
            "http://www.url3.com"
        );
        assert.strictEqual(
            form.$('div[name="url4"].o_field_url > a').attr("href"),
            "https://url4.com"
        );

        form.destroy();
    });

    QUnit.skip("UrlField in editable list view", async function (assert) {
        assert.expect(10);

        var list = await createView({
            View: ListView,
            model: "partner",
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo" widget="url"/></tree>',
        });

        assert.strictEqual(
            list.$("tbody td:not(.o_list_record_selector)").length,
            5,
            "should have 5 cells"
        );
        assert.containsN(
            list,
            "div.o_form_uri.o_field_widget.o_text_overflow.o_field_url > a",
            5,
            "should have 5 anchors with correct classes"
        );
        assert.hasAttrValue(
            list.$("div.o_form_uri.o_field_widget.o_text_overflow.o_field_url > a").first(),
            "href",
            "http://yop",
            "should have proper href link"
        );
        assert.strictEqual(
            list.$("tbody td:not(.o_list_record_selector)").first().text(),
            "yop",
            "value should be displayed properly as text"
        );

        // Edit a line and check the result
        var $cell = list.$("tbody td:not(.o_list_record_selector)").first();
        await testUtils.dom.click($cell);
        assert.hasClass($cell.parent(), "o_selected_row", "should be set as edit mode");
        assert.strictEqual(
            $cell.find("input").val(),
            "yop",
            "should have the corect value in internal input"
        );
        await testUtils.fields.editInput($cell.find("input"), "brolo");

        // save
        await testUtils.dom.click(list.$buttons.find(".o_list_button_save"));
        $cell = list.$("tbody td:not(.o_list_record_selector)").first();
        assert.doesNotHaveClass(
            $cell.parent(),
            "o_selected_row",
            "should not be in edit mode anymore"
        );
        assert.containsN(
            list,
            "div.o_form_uri.o_field_widget.o_text_overflow.o_field_url > a",
            5,
            "should still have 5 anchors with correct classes"
        );
        assert.hasAttrValue(
            list.$("div.o_form_uri.o_field_widget.o_text_overflow.o_field_url > a").first(),
            "href",
            "http://brolo",
            "should have proper new href link"
        );
        assert.strictEqual(
            list.$("div.o_form_uri.o_field_widget.o_text_overflow.o_field_url > a").first().text(),
            "brolo",
            "value should be properly updated"
        );

        list.destroy();
    });

    QUnit.skip("UrlField with falsy value", async function (assert) {
        assert.expect(4);

        this.data.partner.records[0].foo = false;
        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form><field name="foo" widget="url"/></form>',
            res_id: 1,
        });

        assert.containsOnce(form, "div.o_field_widget[name=foo]");
        assert.strictEqual(form.$(".o_field_widget[name=foo]").text(), "");

        await testUtils.form.clickEdit(form);

        assert.containsOnce(form, "input.o_field_widget[name=foo]");
        assert.strictEqual(form.$(".o_field_widget[name=foo]").val(), "");

        form.destroy();
    });

    QUnit.skip("UrlField: url old content is cleaned on render edit", async function (assert) {
        assert.expect(3);

        this.data.partner.fields.foo2 = { string: "Foo2", type: "char", default: "foo2" };
        this.data.partner.onchanges.foo2 = function (record) {
            record.foo = record.foo2;
        };

        const form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: `
                <form string="Partners">
                    <sheet>
                        <group>
                            <field name="foo" widget="url" attrs="{'readonly': True}" />
                            <field name="foo2" />
                        </group>
                    </sheet>
                </form>
                `,
            res_id: 1,
        });

        assert.strictEqual(
            form.$(".o_field_widget[name=foo]").text(),
            "yop",
            "the starting value should be displayed properly"
        );
        await testUtils.form.clickEdit(form);

        assert.strictEqual(
            form.$(".o_field_widget[name=foo2]").val(),
            "foo2",
            "input should contain field value in edit mode"
        );

        await testUtils.fields.editInput(form.$(".o_field_widget[name=foo2]"), "bonjour");
        assert.strictEqual(
            form.$(".o_field_widget[name=foo]").text(),
            "bonjour",
            "Url widget should show the new value and not " +
                form.$(".o_field_widget[name=foo]").text()
        );

        form.destroy();
    });
});
