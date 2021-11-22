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
                        resId: { type: "integer" },
                    },
                    records: [
                        {
                            id: 99,
                            resId: 37,
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

    QUnit.test("UrlField in form view", async function (assert) {
        assert.expect(10);

        const form = await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="foo" widget="url"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            resId: 1,
        });
        const matchingEl = form.el.querySelector("a.o-url-field.o_field_widget.o_form_uri");
        assert.containsOnce(form, matchingEl, "should have a anchor with correct classes");
        assert.hasAttrValue(matchingEl, "href", "http://yop", "should have proper href link");
        assert.hasAttrValue(
            matchingEl,
            "target",
            "_blank",
            "should have target attribute set to _blank"
        );
        assert.strictEqual(matchingEl.innerText, "yop", "the value should be displayed properly");

        // switch to edit mode and check the result
        await click(form.el.querySelector(".o_form_button_edit"));
        assert.containsOnce(
            form,
            'input[type="text"].o_field_widget',
            "should have an input for the char field"
        );
        assert.strictEqual(
            form.el.querySelector('input[type="text"].o_field_widget').value,
            "yop",
            "input should contain field value in edit mode"
        );

        // change value in edit mode
        let editField = form.el.querySelector('input[type="text"].o_field_widget');
        editField.value = "limbo";
        await triggerEvent(editField, null, "change");

        // save
        await click(form.el.querySelector(".o_form_button_save"));
        const editedElement = form.el.querySelector("a.o-url-field.o_field_widget.o_form_uri");
        assert.containsOnce(form, editedElement, "should still have a anchor with correct classes");
        assert.hasAttrValue(
            editedElement,
            "href",
            "http://limbo",
            "should have proper new href link"
        );
        assert.strictEqual(editedElement.innerText, "limbo", "the new value should be displayed");

        await click(form.el.querySelector(".o_form_button_edit"));
        editField = form.el.querySelector('input[type="text"].o_field_widget');
        editField.value = "/web/limbo";
        await triggerEvent(editField, null, "change");

        await click(form.el.querySelector(".o_form_button_save"));
        assert.hasAttrValue(
            form.el.querySelector("a.o-url-field.o_field_widget.o_form_uri"),
            "href",
            "/web/limbo",
            "should'nt have change link"
        );

        form.destroy();
    });

    QUnit.test("UrlField takes text from proper attribute", async function (assert) {
        assert.expect(1);

        const form = await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch:
                '<form string="Partners">' +
                '<field name="foo" widget="url" text="kebeclibre"/>' +
                "</form>",
            resId: 1,
        });

        assert.strictEqual(
            form.el.querySelector('a[name="foo"]').innerText,
            "kebeclibre",
            "url text should come from the text attribute"
        );
        form.destroy();
    });

    QUnit.test("UrlField: href attribute and website_path option", async function (assert) {
        assert.expect(4);

        serverData.models.partner.fields.url1 = {
            string: "Url 1",
            type: "char",
            default: "www.url1.com",
        };
        serverData.models.partner.fields.url2 = {
            string: "Url 2",
            type: "char",
            default: "www.url2.com",
        };
        serverData.models.partner.fields.url3 = {
            string: "Url 3",
            type: "char",
            default: "http://www.url3.com",
        };
        serverData.models.partner.fields.url4 = {
            string: "Url 4",
            type: "char",
            default: "https://url4.com",
        };

        const form = await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <field name="url1" widget="url"/>
                    <field name="url2" widget="url" options="{'website_path': True}"/>
                    <field name="url3" widget="url"/>
                    <field name="url4" widget="url"/>
                </form>`,
            resId: 1,
        });
        assert.strictEqual(
            form.el.querySelector('[name="url1"]').getAttribute("href"),
            "http://www.url1.com"
        );
        assert.strictEqual(
            form.el.querySelector('[name="url2"]').getAttribute("href"),
            "www.url2.com"
        );
        assert.strictEqual(
            form.el.querySelector('[name="url3"]').getAttribute("href"),
            "http://www.url3.com"
        );
        assert.strictEqual(
            form.el.querySelector('[name="url4"]').getAttribute("href"),
            "https://url4.com"
        );

        form.destroy();
    });

    QUnit.skip("UrlField in editable list view", async function (assert) {
        assert.expect(10);

        var list = await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: '<tree editable="bottom"><field name="foo" widget="url"/></tree>',
        });
        assert.strictEqual(
            list.el.querySelectorAll("tbody td:not(.o_list_record_selector)").length,
            5,
            "should have 5 cells"
        );
        assert.containsN(
            list,
            "a.o_field_widget.o_field_url",
            5,
            "should have 5 anchors with correct classes"
        );
        assert.hasAttrValue(
            list.el.querySelector("a.o_field_widget.o_field_url"),
            "href",
            "http://yop",
            "should have proper href link"
        );
        assert.strictEqual(
            list.el.querySelector("tbody td:not(.o_list_record_selector)").innerText,
            "yop",
            "value should be displayed properly as text"
        );

        // Edit a line and check the result
        var cell = list.el.querySelector("tbody td:not(.o_list_record_selector)");
        await testUtils.dom.click(cell);
        assert.hasClass(cell.parentElement, "o_selected_row", "should be set as edit mode");
        assert.strictEqual(
            cell.querySelector("input").value,
            "yop",
            "should have the corect value in internal input"
        );
        await testUtils.fields.editInput(cell.querySelector("input"), "brolo");

        // save
        await click(form.el.querySelector(".o_form_button_save"));
        cell = list.el.querySelector("tbody td:not(.o_list_record_selector)");
        assert.doesNotHaveClass(
            cell.parentElement,
            "o_selected_row",
            "should not be in edit mode anymore"
        );
        const resultEl = list.el.querySelector(
            "div.o_form_uri.o_field_widget.o_text_overflow.o_field_url > a"
        );
        assert.containsN(list, resultEl, 5, "should still have 5 anchors with correct classes");
        assert.hasAttrValue(resultEl, "href", "http://brolo", "should have proper new href link");
        assert.strictEqual(resultEl.innerText, "brolo", "value should be properly updated");

        list.destroy();
    });

    QUnit.test("UrlField with falsy value", async function (assert) {
        assert.expect(4);

        serverData.models.partner.records[0].foo = false;
        const form = await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: '<form><field name="foo" widget="url"/></form>',
            resId: 1,
        });

        assert.containsOnce(form, "[name=foo]");
        assert.strictEqual(form.el.querySelector("[name=foo]").innerText, "");

        await click(form.el.querySelector(".o_form_button_edit"));

        assert.containsOnce(form, "input[name=foo]");
        assert.strictEqual(form.el.querySelector("[name=foo]").value, "");

        form.destroy();
    });

    QUnit.test("UrlField: url old content is cleaned on render edit", async function (assert) {
        assert.expect(3);

        serverData.models.partner.fields.foo2 = { string: "Foo2", type: "char", default: "foo2" };
        serverData.models.partner.onchanges.foo2 = function (record) {
            record.foo = record.foo2;
        };

        const form = await makeView({
            serverData,
            type: "form",
            resModel: "partner",
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
            resId: 1,
        });

        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name=foo]").innerText,
            "yop",
            "the starting value should be displayed properly"
        );
        await click(form.el.querySelector(".o_form_button_edit"));

        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name=foo2]").value,
            "foo2",
            "input should contain field value in edit mode"
        );
        const field = form.el.querySelector(".o_field_widget[name=foo2]");
        field.value = "bonjour";
        await triggerEvent(field, null, "change");
        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name=foo]").innerText,
            "bonjour",
            "Url widget should show the new value and not " +
                form.el.querySelector(".o_field_widget[name=foo]").innerText
        );

        form.destroy();
    });
});
