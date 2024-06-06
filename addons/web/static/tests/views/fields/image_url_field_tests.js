/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";
import {
    click,
    editInput,
    getFixture,
    nextTick,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;
const FR_FLAG_URL = "/base/static/img/country_flags/fr.png";
const EN_FLAG_URL = "/base/static/img/country_flags/gb.png";

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char", searchable: true },
                        foo: {
                            string: "Foo",
                            type: "char",
                            default: "My little Foo Value",
                            searchable: true,
                            trim: true,
                        },
                        p: {
                            string: "one2many field",
                            type: "one2many",
                            relation: "partner",
                            searchable: true,
                        },
                        timmy: {
                            string: "pokemon",
                            type: "many2many",
                            relation: "partner_type",
                            searchable: true,
                        },
                    },
                    records: [
                        {
                            id: 1,
                            foo: FR_FLAG_URL,
                            timmy: [],
                        },
                    ],
                    onchanges: {},
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
            },
        };

        setupViewRegistries();
    });

    /**
     * Same tests than for Image fields, but for Char fields with image_url widget.
     */
    QUnit.module("ImageUrlField");

    QUnit.test("image fields are correctly rendered", async function (assert) {
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <field name="foo" widget="image_url" options="{'size': [90, 90]}"/>
                </form>`,
            resId: 1,
        });

        assert.hasClass(
            target.querySelector('div[name="foo"]'),
            "o_field_image_url",
            "the widget should have the correct class"
        );
        assert.containsOnce(target, 'div[name="foo"] > img', "the widget should contain an image");
        assert.strictEqual(
            target.querySelector('div[name="foo"] > img').dataset.src,
            FR_FLAG_URL,
            "the image should have the correct src"
        );
        assert.hasClass(
            target.querySelector('div[name="foo"] > img'),
            "img-fluid",
            "the image should have the correct class"
        );
        assert.hasAttrValue(
            target.querySelector('div[name="foo"] > img'),
            "width",
            "90",
            "the image should correctly set its attributes"
        );
        assert.strictEqual(
            target.querySelector('div[name="foo"] > img').style.maxWidth,
            "90px",
            "the image should correctly set its attributes"
        );
    });

    QUnit.test("ImageUrlField in subviews are loaded correctly", async function (assert) {
        serverData.models.partner_type.fields.image = { name: "image", type: "char" };
        serverData.models.partner_type.records[0].image = EN_FLAG_URL;
        serverData.models.partner.records[0].timmy = [12];

        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <field name="foo" widget="image_url" options="{'size': [90, 90]}"/>
                    <field name="timmy" widget="many2many" mode="kanban">
                        <kanban>
                            <field name="display_name"/>
                            <templates>
                                <t t-name="kanban-box">
                                    <div class="oe_kanban_global_click">
                                        <span><t t-esc="record.display_name.value"/></span>
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                        <form>
                            <field name="image" widget="image_url"/>
                        </form>
                    </field>
                </form>`,
            resId: 1,
        });

        assert.ok(
            document.querySelector(`img[data-src="${FR_FLAG_URL}"]`),
            "The view's image is in the DOM"
        );
        assert.containsOnce(
            target,
            ".o_kanban_record .oe_kanban_global_click",
            "There should be one record in the many2many"
        );

        // Actual flow: click on an element of the m2m to get its form view
        await click(target.querySelector(".oe_kanban_global_click"));
        assert.containsOnce(document.body, ".modal", "The modal should have opened");

        assert.ok(
            document.querySelector(`img[data-src="${EN_FLAG_URL}"]`),
            "The dialog's image is in the DOM"
        );
    });

    QUnit.test("image fields in x2many list are loaded correctly", async function (assert) {
        serverData.models.partner_type.fields.image = { name: "image", type: "char" };
        serverData.models.partner_type.records[0].image = EN_FLAG_URL;
        serverData.models.partner.records[0].timmy = [12];

        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <field name="timmy" widget="many2many">
                        <tree>
                            <field name="image" widget="image_url"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(target, "tr.o_data_row", "There should be one record in the many2many");
        assert.ok(
            document.querySelector(`img[data-src="${EN_FLAG_URL}"]`),
            "The list's image is in the DOM"
        );
    });

    QUnit.test("image url fields in kanban don't stop opening record", async function (assert) {
        patchWithCleanup(KanbanController.prototype, {
            openRecord() {
                assert.step("open record");
            },
        });

        await makeView({
            type: "kanban",
            serverData,
            resModel: "partner",
            arch: /* xml */ `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div class="oe_kanban_global_click">
                                <field name="foo" widget="image_url"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        });

        await click(target.querySelector(".o_kanban_record"));
        assert.verifySteps(["open record"]);
    });

    QUnit.test("image fields with empty value", async function (assert) {
        serverData.models.partner.records[0].foo = false;

        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <field name="foo" widget="image_url" options="{'size': [90, 90]}"/>
                </form>`,
            resId: 1,
        });

        assert.hasClass(
            target.querySelector('div[name="foo"]'),
            "o_field_image_url",
            "the widget should have the correct class"
        );
        assert.containsNone(
            target,
            'div[name="foo"] > img',
            "the widget should not contain an image"
        );
    });

    QUnit.test("onchange update image fields", async function (assert) {
        const srcTest = "/my/test/src";
        serverData.models.partner.onchanges = {
            display_name(record) {
                record.foo = srcTest;
            },
        };

        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <field name="display_name"/>
                    <field name="foo" widget="image_url" options="{'size': [90, 90]}"/>
                </form>`,
            resId: 1,
        });

        assert.strictEqual(
            target.querySelector('div[name="foo"] > img').dataset.src,
            FR_FLAG_URL,
            "the image should have the correct src"
        );

        await editInput(target, '[name="display_name"] input', "test");
        await nextTick();
        assert.strictEqual(
            target.querySelector('div[name="foo"] > img').dataset.src,
            srcTest,
            "the image should have the onchange src"
        );
    });
});
