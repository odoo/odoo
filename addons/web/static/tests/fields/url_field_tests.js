/** @odoo-module **/

import { click, editInput, getFixture } from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

let serverData, target;

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
                            trim: true,
                        },
                    },
                    records: [
                        {
                            foo: "yop",
                        },
                        {
                            foo: "blip",
                        },
                    ],
                    onchanges: {},
                },
            },
        };
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.module("UrlField");

    QUnit.test("UrlField in form view", async function (assert) {
        assert.expect(10);

        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form string="Partners">
                    <sheet>
                        <group>
                            <field name="foo" widget="url"/>
                        </group>
                    </sheet>
                </form>`,
            resId: 1,
        });
        const matchingEl = target.querySelector("a.o_url_field.o_field_widget.o_form_uri");
        assert.containsOnce(target, matchingEl, "should have a anchor with correct classes");
        assert.hasAttrValue(matchingEl, "href", "http://yop", "should have proper href link");
        assert.hasAttrValue(
            matchingEl,
            "target",
            "_blank",
            "should have target attribute set to _blank"
        );
        assert.strictEqual(matchingEl.textContent, "yop", "the value should be displayed properly");

        // switch to edit mode and check the result
        await click(target.querySelector(".o_form_button_edit"));
        assert.containsOnce(
            target,
            '.o_field_widget input[type="text"]',
            "should have an input for the char field"
        );
        assert.strictEqual(
            target.querySelector('.o_field_widget input[type="text"]').value,
            "yop",
            "input should contain field value in edit mode"
        );

        await editInput(target, ".o_field_widget input[type='text']", "limbo");

        // save
        await click(target.querySelector(".o_form_button_save"));
        const editedElement = target.querySelector("a.o_url_field.o_field_widget.o_form_uri");
        assert.containsOnce(
            target,
            editedElement,
            "should still have a anchor with correct classes"
        );
        assert.hasAttrValue(
            editedElement,
            "href",
            "http://limbo",
            "should have proper new href link"
        );
        assert.strictEqual(editedElement.textContent, "limbo", "the new value should be displayed");

        await click(target.querySelector(".o_form_button_edit"));
        await editInput(target, ".o_field_widget input[type='text']", "/web/limbo");

        await click(target.querySelector(".o_form_button_save"));
        assert.hasAttrValue(
            target.querySelector(".o_field_widget[name='foo'] a"),
            "href",
            "/web/limbo",
            "shouldn't have change link"
        );
    });

    QUnit.test("UrlField takes text from proper attribute", async function (assert) {
        assert.expect(1);

        await makeView({
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
            target.querySelector('.o_field_widget[name="foo"] a').textContent,
            "kebeclibre",
            "url text should come from the text attribute"
        );
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

        await makeView({
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
            target.querySelector('.o_field_widget[name="url1"] a').getAttribute("href"),
            "http://www.url1.com"
        );
        assert.strictEqual(
            target.querySelector('.o_field_widget[name="url2"] a').getAttribute("href"),
            "www.url2.com"
        );
        assert.strictEqual(
            target.querySelector('.o_field_widget[name="url3"] a').getAttribute("href"),
            "http://www.url3.com"
        );
        assert.strictEqual(
            target.querySelector('.o_field_widget[name="url4"] a').getAttribute("href"),
            "https://url4.com"
        );
    });

    QUnit.test("UrlField in editable list view", async function (assert) {
        assert.expect(10);

        await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: '<tree editable="bottom"><field name="foo" widget="url"/></tree>',
        });
        assert.strictEqual(
            target.querySelectorAll("tbody td:not(.o_list_record_selector) a").length,
            2,
            "should have 2 cells with a link"
        );
        assert.containsN(
            target,
            ".o_field_url.o_field_widget[name='foo'] a",
            2,
            "should have 2 anchors with correct classes"
        );
        assert.hasAttrValue(
            target.querySelector(".o_field_widget[name='foo'] a"),
            "href",
            "http://yop",
            "should have proper href link"
        );
        assert.strictEqual(
            target.querySelector("tbody td:not(.o_list_record_selector)").textContent,
            "yop",
            "value should be displayed properly as text"
        );

        // Edit a line and check the result
        let cell = target.querySelector("tbody td:not(.o_list_record_selector)");
        await click(cell);
        assert.hasClass(cell.parentElement, "o_selected_row", "should be set as edit mode");
        assert.strictEqual(
            cell.querySelector("input").value,
            "yop",
            "should have the correct value in internal input"
        );
        await editInput(cell, "input", "brolo");

        // save
        await click(target.querySelector(".o_list_button_save"));
        cell = target.querySelector("tbody td:not(.o_list_record_selector)");
        assert.doesNotHaveClass(
            cell.parentElement,
            "o_selected_row",
            "should not be in edit mode anymore"
        );
        const resultEl = target.querySelector(".o_field_widget[name='foo'] a");
        assert.containsN(
            target,
            ".o_field_widget[name='foo'] a",
            2,
            "should still have anchors with correct classes"
        );
        assert.hasAttrValue(resultEl, "href", "http://brolo", "should have proper new href link");
        assert.strictEqual(resultEl.textContent, "brolo", "value should be properly updated");
    });

    QUnit.test("UrlField with falsy value", async function (assert) {
        assert.expect(4);

        serverData.models.partner.records[0].foo = false;
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: '<form><field name="foo" widget="url"/></form>',
            resId: 1,
        });

        assert.containsOnce(target, "[name=foo]");
        assert.strictEqual(target.querySelector("[name=foo]").textContent, "");

        await click(target.querySelector(".o_form_button_edit"));

        assert.containsOnce(target, ".o_field_widget[name=foo] input");
        assert.strictEqual(target.querySelector("[name=foo] input").value, "");
    });

    QUnit.test("UrlField: url old content is cleaned on render edit", async function (assert) {
        assert.expect(3);

        serverData.models.partner.fields.foo2 = { string: "Foo2", type: "char", default: "foo2" };
        serverData.models.partner.onchanges.foo2 = function (record) {
            record.foo = record.foo2;
        };

        await makeView({
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
            target.querySelector(".o_field_widget[name=foo]").textContent,
            "yop",
            "the starting value should be displayed properly"
        );
        await click(target.querySelector(".o_form_button_edit"));

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo2] input").value,
            "foo2",
            "input should contain field value in edit mode"
        );
        await editInput(target, ".o_field_widget[name=foo2] input", "bonjour");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo]").textContent,
            "bonjour",
            "Url widget should show the new value and not " +
                target.querySelector(".o_field_widget[name=foo]").textContent
        );
    });
});
