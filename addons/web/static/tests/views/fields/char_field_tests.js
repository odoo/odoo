/** @odoo-module **/

import { registry } from "@web/core/registry";
import {
    click,
    clickSave,
    editInput,
    getFixture,
    makeDeferred,
    nextTick,
    patchWithCleanup,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import { session } from "@web/session";

const serviceRegistry = registry.category("services");

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
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
                        int_field: {
                            string: "int_field",
                            type: "integer",
                            sortable: true,
                            searchable: true,
                        },
                        p: {
                            string: "one2many field",
                            type: "one2many",
                            relation: "partner",
                            searchable: true,
                        },
                        product_id: {
                            string: "Product",
                            type: "many2one",
                            relation: "product",
                            searchable: true,
                        },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "first record",
                            foo: "yop",
                            int_field: 10,
                            p: [],
                        },
                        {
                            id: 2,
                            display_name: "second record",
                            foo: "blip",
                            int_field: 0,
                            p: [],
                        },
                        { id: 3, foo: "gnap", int_field: 80 },
                        {
                            id: 4,
                            display_name: "aaa",
                            foo: "abc",
                            int_field: false,
                        },
                        { id: 5, foo: "blop", int_field: -4 },
                    ],
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
            },
        };

        setupViewRegistries();
    });

    QUnit.module("CharField");

    QUnit.test("char field in form view", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="foo" />
                        </group>
                    </sheet>
                </form>`,
        });

        assert.containsOnce(
            target,
            ".o_field_widget input[type='text']",
            "should have an input for the char field"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget input[type='text']").value,
            "yop",
            "input should contain field value in edit mode"
        );

        // change value in edit mode
        await editInput(target, ".o_field_widget input[type='text']", "limbo");

        // save
        await clickSave(target);
        assert.strictEqual(
            target.querySelector(".o_field_widget input[type='text']").value,
            "limbo",
            "the new value should be displayed"
        );
    });

    QUnit.test(
        "setting a char field to empty string is saved as a false value",
        async function (assert) {
            assert.expect(1);

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="foo" />
                            </group>
                        </sheet>
                    </form>`,
                resId: 1,
                mockRPC(route, { args, method }) {
                    if (method === "web_save") {
                        assert.strictEqual(args[1].foo, false, "the foo value should be false");
                    }
                },
            });

            await editInput(target, ".o_field_widget input[type='text']", "");
            await clickSave(target);
        }
    );

    QUnit.test("char field with size attribute", async function (assert) {
        serverData.models.partner.fields.foo.size = 5; // max length

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="foo" />
                        </group>
                    </sheet>
                </form>`,
        });
        assert.hasAttrValue(
            target.querySelector("input"),
            "maxlength",
            "5",
            "maxlength attribute should have been set correctly on the input"
        );
    });

    QUnit.test("char field in editable list view", async function (assert) {
        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="foo" />
                </tree>`,
        });

        assert.containsN(target, "tbody td:not(.o_list_record_selector)", 5, "should have 5 cells");
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
            "should have the corect value in internal input"
        );

        await editInput(cell, "input", "brolo");

        // save
        await clickSave(target);
        cell = target.querySelector("tbody td:not(.o_list_record_selector)");
        assert.doesNotHaveClass(
            cell.parentElement,
            "o_selected_row",
            "should not be in edit mode anymore"
        );
        assert.strictEqual(
            target.querySelector("tbody td:not(.o_list_record_selector)").textContent,
            "brolo",
            "value should be properly updated"
        );
    });

    QUnit.test("char field translatable", async function (assert) {
        assert.expect(13);

        serverData.models.partner.fields.foo.translate = true;
        serviceRegistry.add("localization", makeFakeLocalizationService({ multiLang: true }), {
            force: true,
        });
        patchWithCleanup(session.user_context, {
            lang: "en_US",
        });
        let call_get_field_translations = 0;

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="foo" />
                        </group>
                    </sheet>
                </form>`,
            mockRPC(route, { args, method, model }) {
                if (route === "/web/dataset/call_kw/res.lang/get_installed") {
                    return Promise.resolve([
                        ["en_US", "English"],
                        ["fr_BE", "French (Belgium)"],
                        ["es_ES", "Spanish"],
                    ]);
                }
                if (route === "/web/dataset/call_kw/partner/get_field_translations") {
                    if (call_get_field_translations === 0) {
                        call_get_field_translations = 1;
                        return Promise.resolve([
                            [
                                { lang: "en_US", source: "yop", value: "yop" },
                                { lang: "fr_BE", source: "yop", value: "yop français" },
                                { lang: "es_ES", source: "yop", value: "yop español" },
                            ],
                            { translation_type: "char", translation_show_source: false },
                        ]);
                    }
                    if (call_get_field_translations === 1) {
                        return Promise.resolve([
                            [
                                { lang: "en_US", source: "bar", value: "bar" },
                                { lang: "fr_BE", source: "bar", value: "yop français" },
                                { lang: "es_ES", source: "bar", value: "bar" },
                            ],
                            { translation_type: "char", translation_show_source: false },
                        ]);
                    }
                }
                if (route === "/web/dataset/call_kw/partner/update_field_translations") {
                    assert.deepEqual(
                        args[2],
                        { en_US: "bar", es_ES: false },
                        "the new translation value should be written and the value false voids the translation"
                    );
                    serverData.models.partner.records[0].foo = "bar";
                    return Promise.resolve(null);
                }
            },
        });

        assert.hasClass(target.querySelector("[name=foo] input"), "o_field_translate");

        assert.containsOnce(
            target,
            ".o_field_char .btn.o_field_translate",
            "should have a translate button"
        );
        assert.strictEqual(
            target.querySelector(".o_field_char .btn.o_field_translate").textContent,
            "EN",
            "the button should have as test the current language"
        );
        await click(target, ".o_field_char .btn.o_field_translate");

        assert.containsOnce(target, ".modal", "a translate modal should be visible");
        assert.containsN(
            target,
            ".modal .o_translation_dialog .translation",
            3,
            "three rows should be visible"
        );

        let translations = target.querySelectorAll(
            ".modal .o_translation_dialog .translation input"
        );
        assert.strictEqual(translations[0].value, "yop", "English translation should be filled");
        assert.strictEqual(
            translations[1].value,
            "yop français",
            "French translation should be filled"
        );
        assert.strictEqual(
            translations[2].value,
            "yop español",
            "Spanish translation should be filled"
        );

        await editInput(translations[0], null, "bar"); // set the en_US(user language) translation to "foo"
        await editInput(translations[2], null, ""); // void the es_ES translation
        await click(target, ".modal button.btn-primary"); // save

        assert.strictEqual(
            target.querySelector(`.o_field_char input[type="text"]`).value,
            "bar",
            "the new translation was not transfered to modified record"
        );

        await editInput(target, `.o_field_char input[type="text"]`, "baz");
        await click(target, ".o_field_char .btn.o_field_translate");

        translations = target.querySelectorAll(".modal .o_translation_dialog .translation input");
        assert.strictEqual(
            translations[0].value,
            "baz",
            "Modified value should be used instead of translation"
        );
        assert.strictEqual(
            translations[1].value,
            "yop français",
            "French translation shouldn't be changed"
        );
        assert.strictEqual(
            translations[2].value,
            "bar",
            "Spanish translation should fallback to the English translation"
        );
    });

    QUnit.test(
        "translation dialog should close if field is not there anymore",
        async function (assert) {
            // In this test, we simulate the case where the field is removed from the view
            // this can happend for example if the user click the back button of the browser.
            serverData.models.partner.fields.foo.translate = true;
            serviceRegistry.add("localization", makeFakeLocalizationService({ multiLang: true }), {
                force: true,
            });
            patchWithCleanup(session.user_context, {
                lang: "en_US",
            });
            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="int_field" />
                            <field name="foo"  invisible="int_field == 9"/>
                        </group>
                    </sheet>
                </form>`,
                mockRPC(route, { args, method, model }) {
                    if (route === "/web/dataset/call_kw/res.lang/get_installed") {
                        return Promise.resolve([
                            ["en_US", "English"],
                            ["fr_BE", "French (Belgium)"],
                            ["es_ES", "Spanish"],
                        ]);
                    }
                    if (route === "/web/dataset/call_kw/partner/get_field_translations") {
                        return Promise.resolve([
                            [
                                { lang: "en_US", source: "yop", value: "yop" },
                                { lang: "fr_BE", source: "yop", value: "valeur français" },
                                { lang: "es_ES", source: "yop", value: "yop español" },
                            ],
                            { translation_type: "char", translation_show_source: false },
                        ]);
                    }
                },
            });

            assert.hasClass(target.querySelector("[name=foo] input"), "o_field_translate");

            await click(target, ".o_field_char .btn.o_field_translate");
            assert.containsOnce(target, ".modal", "a translate modal should be visible");
            await editInput(target, ".o_field_widget[name=int_field] input", "9");
            await nextTick();
            assert.containsNone(target, "[name=foo] input", "the field foo should be invisible");
            assert.containsNone(target, ".modal", "a translate modal should not be visible");
        }
    );

    QUnit.test("html field translatable", async function (assert) {
        assert.expect(5);

        serverData.models.partner.fields.foo.translate = true;
        serviceRegistry.add("localization", makeFakeLocalizationService({ multiLang: true }), {
            force: true,
        });
        patchWithCleanup(session.user_context, {
            lang: "en_US",
        });

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="foo" />
                        </group>
                    </sheet>
                </form>`,
            mockRPC(route, { args, method, model }) {
                if (route === "/web/dataset/call_kw/res.lang/get_installed") {
                    return Promise.resolve([
                        ["en_US", "English"],
                        ["fr_BE", "French (Belgium)"],
                    ]);
                }
                if (route === "/web/dataset/call_kw/partner/get_field_translations") {
                    return Promise.resolve([
                        [
                            {
                                lang: "en_US",
                                source: "first paragraph",
                                value: "first paragraph",
                            },
                            {
                                lang: "en_US",
                                source: "second paragraph",
                                value: "second paragraph",
                            },
                            {
                                lang: "fr_BE",
                                source: "first paragraph",
                                value: "premier paragraphe",
                            },
                            {
                                lang: "fr_BE",
                                source: "second paragraph",
                                value: "deuxième paragraphe",
                            },
                        ],
                        {
                            translation_type: "char",
                            translation_show_source: true,
                        },
                    ]);
                }

                if (route === "/web/dataset/call_kw/partner/update_field_translations") {
                    assert.deepEqual(
                        args[2],
                        { en_US: { "first paragraph": "first paragraph modified" } },
                        "the new translation value should be written"
                    );
                    return Promise.resolve(null);
                }
            },
        });

        // this will not affect the translate_fields effect until the record is
        // saved but is set for consistency of the test
        await editInput(
            target,
            `.o_field_char input[type="text"]`,
            "<p>first paragraph</p><p>second paragraph</p>"
        );

        await click(target, ".o_field_char .btn.o_field_translate");
        assert.containsOnce(target, ".modal", "a translate modal should be visible");
        assert.containsN(
            target,
            ".modal .o_translation_dialog .translation",
            4,
            "four rows should be visible"
        );

        const enField = target.querySelector(".modal .o_translation_dialog .translation input");
        assert.strictEqual(
            enField.value,
            "first paragraph",
            "first part of english translation should be filled"
        );

        await editInput(enField, null, "first paragraph modified");
        await click(target, ".modal button.btn-primary"); // save

        assert.strictEqual(
            target.querySelector(`.o_field_char input[type="text"]`).value,
            "<p>first paragraph</p><p>second paragraph</p>",
            "the new partial translation should not be transfered"
        );
    });

    QUnit.test("char field translatable in create mode", async function (assert) {
        assert.expect(1);

        serverData.models.partner.fields.foo.translate = true;
        serviceRegistry.add("localization", makeFakeLocalizationService({ multiLang: true }), {
            force: true,
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="foo" />
                        </group>
                    </sheet>
                </form>`,
        });

        assert.containsOnce(
            target,
            `.o_field_char .btn.o_field_translate`,
            "should have a translate button in create mode"
        );
    });

    QUnit.test("char field does not allow html injections", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="foo" />
                        </group>
                    </sheet>
                </form>`,
        });

        await editInput(target, "[name='foo'] input", "<script>throw Error();</script>");
        await clickSave(target);
        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "<script>throw Error();</script>",
            "the value should have been properly escaped"
        );
    });

    QUnit.test("char field trim (or not) characters", async function (assert) {
        serverData.models.partner.fields.foo2 = { string: "Foo2", type: "char", trim: false };

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="foo" />
                            <field name="foo2" />
                        </group>
                    </sheet>
                </form>`,
        });

        await editInput(target, ".o_field_widget[name='foo'] input", "  abc  ");
        await editInput(target, ".o_field_widget[name='foo2'] input", "  def  ");
        await clickSave(target);
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='foo'] input").value,
            "abc",
            "Foo value should have been trimmed"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='foo2'] input").value,
            "  def  ",
            "Foo2 value should not have been trimmed"
        );
    });

    QUnit.test(
        "input field: change value before pending onchange returns",
        async function (assert) {
            serverData.models.partner.onchanges = {
                product_id() {},
            };

            let def;
            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <field name="p">
                                <tree editable="bottom">
                                    <field name="product_id" />
                                    <field name="foo" />
                                </tree>
                            </field>
                        </sheet>
                    </form>`,
                async mockRPC(route, { method }) {
                    if (method === "onchange") {
                        await def;
                    }
                },
            });

            await click(target, ".o_field_x2many_list_row_add a");
            assert.strictEqual(
                target.querySelector(".o_field_widget[name='foo'] input").value,
                "My little Foo Value",
                "should contain the default value"
            );

            def = makeDeferred();
            await click(target, ".o-autocomplete--input");
            await click(target.querySelector(".o-autocomplete--dropdown-item"));

            // set foo before onchange
            await editInput(target, ".o_field_widget[name='foo'] input", "tralala");
            assert.strictEqual(
                target.querySelector(".o_field_widget[name='foo'] input").value,
                "tralala",
                "input should contain tralala"
            );

            // complete the onchange
            def.resolve();
            await nextTick();
            assert.strictEqual(
                target.querySelector(".o_field_widget[name='foo'] input").value,
                "tralala",
                "input should contain the same value as before onchange"
            );
        }
    );

    QUnit.test(
        "input field: change value before pending onchange returns (with fieldDebounce)",
        async function (assert) {
            // this test is exactly the same as the previous one, except that in
            // this scenario the onchange return *before* we validate the change
            // on the input field (before the "change" event is triggered).
            serverData.models.partner.onchanges = {
                product_id(obj) {
                    obj.int_field = obj.product_id ? 7 : false;
                },
            };

            let def;
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="product_id"/>
                                <field name="foo"/>
                                <field name="int_field"/>
                            </tree>
                        </field>
                    </form>`,
                async mockRPC(route, { method }) {
                    if (method === "onchange") {
                        await def;
                    }
                },
            });

            await click(target, ".o_field_x2many_list_row_add a");
            assert.strictEqual(
                target.querySelector(".o_field_widget[name='foo'] input").value,
                "My little Foo Value",
                "should contain the default value"
            );

            def = makeDeferred();
            await click(target, ".o-autocomplete--input");
            await click(target.querySelector(".o-autocomplete--dropdown-item"));

            // set foo before onchange
            target.querySelector(".o_field_widget[name='foo'] input").value = "tralala";
            await triggerEvent(target, ".o_field_widget[name='foo'] input", "input");
            assert.strictEqual(
                target.querySelector(".o_field_widget[name='foo'] input").value,
                "tralala",
                "input should contain tralala"
            );
            assert.strictEqual(
                target.querySelector(".o_field_widget[name='int_field'] input").value,
                ""
            );

            // complete the onchange
            def.resolve();
            await nextTick();
            assert.strictEqual(
                target.querySelector(".o_field_widget[name='foo'] input").value,
                "tralala",
                "foo should contain the same value as before onchange"
            );
            assert.strictEqual(
                target.querySelector(".o_field_widget[name='int_field'] input").value,
                "7",
                "int_field should contain the value returned by the onchange"
            );
        }
    );

    QUnit.test("onchange return value before editing input", async function (assert) {
        serverData.models.partner.onchanges = {
            foo(obj) {
                obj.foo = "yop";
            },
        };

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="foo" />
                </form>`,
        });

        assert.strictEqual(target.querySelector("[name='foo'] input").value, "yop");

        await editInput(target, "[name='foo'] input", "tralala");
        assert.strictEqual(target.querySelector("[name='foo'] input").value, "yop");
    });

    QUnit.test(
        "input field: change value before pending onchange renaming",
        async function (assert) {
            serverData.models.partner.onchanges = {
                product_id(obj) {
                    obj.foo = "on change value";
                },
            };

            const def = makeDeferred();
            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <field name="product_id" />
                            <field name="foo" />
                        </sheet>
                    </form>`,
                async mockRPC(route, { method }) {
                    if (method === "onchange") {
                        await def;
                    }
                },
            });

            assert.strictEqual(
                target.querySelector(".o_field_widget[name='foo'] input").value,
                "yop",
                "should contain the correct value"
            );

            await click(target, ".o-autocomplete--input");
            await click(target.querySelector(".o-autocomplete--dropdown-item"));

            // set foo before onchange
            editInput(target, ".o_field_widget[name='foo'] input", "tralala");
            assert.strictEqual(
                target.querySelector(".o_field_widget[name='foo'] input").value,
                "tralala",
                "should contain tralala"
            );

            // complete the onchange
            def.resolve();
            await nextTick();
            assert.strictEqual(
                target.querySelector(".o_field_widget[name='foo'] input").value,
                "tralala",
                "input should contain the same value as before onchange"
            );
        }
    );

    QUnit.test("support autocomplete attribute", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="display_name" autocomplete="coucou"/></form>`,
            resId: 1,
        });

        assert.hasAttrValue(
            target.querySelector('.o_field_widget[name="display_name"] input'),
            "autocomplete",
            "coucou",
            "attribute autocomplete should be set"
        );
    });

    QUnit.test("input autocomplete attribute set to none by default", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="display_name"/></form>`,
            resId: 1,
        });

        assert.hasAttrValue(
            target.querySelector('.o_field_widget[name="display_name"] input'),
            "autocomplete",
            "off",
            "attribute autocomplete should be set to none by default"
        );
    });

    QUnit.test("support password attribute", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="foo" password="True"/></form>`,
            resId: 1,
        });

        assert.strictEqual(
            target.querySelector('.o_field_widget[name="foo"] input').value,
            "yop",
            "input value should be the password"
        );
        assert.strictEqual(
            target.querySelector('.o_field_widget[name="foo"] input').type,
            "password",
            "input should be of type password"
        );
    });

    QUnit.test("input field: readonly password", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="foo" password="True" readonly="1" />
                </form>`,
        });

        assert.notEqual(
            target.querySelector(".o_field_char").textContent,
            "yop",
            "password field value should not be visible in read mode"
        );
        assert.strictEqual(
            target.querySelector(".o_field_char").textContent,
            "***",
            "password field value should be hidden with '*' in read mode"
        );
    });

    QUnit.test("input field: change password value", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="foo" password="True" />
                </form>`,
        });

        assert.hasAttrValue(
            target.querySelector(".o_field_char input"),
            "type",
            "password",
            "password field input should be with type 'password' in edit mode"
        );
        assert.strictEqual(
            target.querySelector(".o_field_char input").value,
            "yop",
            "password field input value should be the (non-hidden) password value"
        );
    });

    QUnit.test("input field: empty password", async function (assert) {
        serverData.models.partner.records[0].foo = false;

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="foo" password="True" />
                </form>`,
        });

        assert.hasAttrValue(
            target.querySelector(".o_field_char input"),
            "type",
            "password",
            "password field input should be with type 'password' in edit mode"
        );
        assert.strictEqual(
            target.querySelector(".o_field_char input").value,
            "",
            "password field input value should be the (non-hidden, empty) password value"
        );
    });

    QUnit.test(
        "input field: set and remove value, then wait for onchange",
        async function (assert) {
            serverData.models.partner.onchanges = {
                product_id(obj) {
                    obj.foo = obj.product_id ? "onchange value" : false;
                },
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="product_id"/>
                                <field name="foo"/>
                            </tree>
                        </field>
                    </form>`,
            });

            await click(target, ".o_field_x2many_list_row_add a");
            assert.strictEqual(target.querySelector(".o_field_widget[name=foo] input").value, "");

            // set value for foo
            target.querySelector(".o_field_widget[name=foo] input").value = "test";
            await triggerEvent(target, ".o_field_widget[name=foo] input", "input");
            // remove value for foo
            target.querySelector(".o_field_widget[name=foo] input").value = "";
            await triggerEvent(target, ".o_field_widget[name=foo] input", "input");

            // trigger the onchange by setting a product
            await click(target, ".o-autocomplete--input");
            await click(target.querySelector(".o-autocomplete--dropdown-item"));
            assert.strictEqual(
                target.querySelector(".o_field_widget[name=foo] input").value,
                "onchange value",
                "input should contain correct value after onchange"
            );
        }
    );

    QUnit.test("char field with placeholder", async function (assert) {
        serverData.models.partner.fields.foo.default = false;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="foo" placeholder="Placeholder" />
                        </group>
                    </sheet>
                </form>`,
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget[name='foo'] input").placeholder,
            "Placeholder"
        );
    });

    QUnit.test(
        "char field: correct value is used to evaluate the modifiers",
        async function (assert) {
            serverData.models.partner.onchanges = {
                foo: (obj) => {
                    if (obj.foo === "a") {
                        obj.display_name = false;
                    } else if (obj.foo === "b") {
                        obj.display_name = "";
                    }
                },
            };
            serverData.models.partner.records[0].foo = false;
            serverData.models.partner.records[0].display_name = false;

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                resId: 1,
                arch: `
                <form>
                    <field name="foo" />
                    <field name="display_name" invisible="'' == display_name"/>
                </form>`,
            });
            assert.containsOnce(target, "[name='display_name'] input");

            await editInput(target, "[name='foo'] input", "a");
            assert.containsOnce(target, "[name='display_name'] input");

            await editInput(target, "[name='foo'] input", "b");
            assert.containsNone(target, "[name='display_name'] input");
        }
    );

    QUnit.test(
        "edit a char field should display the status indicator buttons without flickering",
        async function (assert) {
            serverData.models.partner.records[0].p = [2];
            serverData.models.partner.onchanges = {
                foo() {},
            };

            const def = makeDeferred();
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                resId: 1,
                arch: `
                    <form>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="foo"/>
                            </tree>
                        </field>
                    </form>`,
                async mockRPC(route, { method }) {
                    if (method === "onchange") {
                        assert.step("onchange");
                        await def;
                    }
                },
            });
            assert.containsOnce(
                target,
                ".o_form_status_indicator_buttons.invisible",
                "form view is not dirty"
            );

            await click(target, ".o_data_cell");
            await editInput(target, "[name='foo'] input", "a");
            assert.verifySteps(["onchange"]);
            assert.containsOnce(
                target,
                ".o_form_status_indicator_buttons:not(.invisible)",
                "form view is dirty"
            );

            def.resolve();
            await nextTick();
            assert.containsOnce(
                target,
                ".o_form_status_indicator_buttons:not(.invisible)",
                "form view is dirty"
            );
        }
    );
});
