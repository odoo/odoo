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
                            bar: true,
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

    QUnit.module("CharField");

    QUnit.skip("char widget isValid method works", async function (assert) {
        // assert.expect(1);
        // serverData.models.partner.fields.foo.required = true;
        // const form = await makeView({
        //     type: "form",
        //     resModel: "partner",
        //     resId: 1,
        //     serverData,
        //     arch: `
        //         <form>
        //             <field name="foo" />
        //         </form>
        //     `,
        // });
        // const charField = _.find(form.renderer.allFieldWidgets)[0];
        // assert.strictEqual(charField.isValid(), true);
    });

    QUnit.test("char field in form view", async function (assert) {
        assert.expect(4);

        const form = await makeView({
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
                </form>
            `,
        });

        assert.strictEqual(
            form.el.querySelector(".o_field_widget").textContent,
            "yop",
            "the value should be displayed properly"
        );

        // switch to edit mode and check the result
        await click(form.el, ".o_form_button_edit");
        assert.containsOnce(
            form.el,
            "input[type='text'].o_field_widget",
            "should have an input for the char field"
        );
        assert.strictEqual(
            form.el.querySelector("input[type='text'].o_field_widget").value,
            "yop",
            "input should contain field value in edit mode"
        );

        // change value in edit mode
        const input = form.el.querySelector("input[type='text'].o_field_widget");
        input.value = "limbo";
        await triggerEvent(input, null, "change");

        // save
        await click(form.el, ".o_form_button_save");
        assert.strictEqual(
            form.el.querySelector(".o_field_widget").textContent,
            "limbo",
            "the new value should be displayed"
        );
    });

    QUnit.test(
        "setting a char field to empty string is saved as a false value",
        async function (assert) {
            assert.expect(1);

            const form = await makeView({
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
                    </form>
                `,
                resId: 1,
                mockRPC(route, { args, method }) {
                    if (method === "write") {
                        assert.strictEqual(args[1].foo, false, "the foo value should be false");
                    }
                },
            });

            await click(form.el, ".o_form_button_edit");

            const input = form.el.querySelector("input[type='text'].o_field_widget");
            input.value = "";
            await triggerEvent(input, null, "change");

            // save
            await click(form.el, ".o_form_button_save");
        }
    );

    QUnit.test("char field with size attribute", async function (assert) {
        assert.expect(1);

        serverData.models.partner.fields.foo.size = 5; // max length

        const form = await makeView({
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
                </form>
            `,
        });

        await click(form.el, ".o_form_button_edit");

        assert.hasAttrValue(
            form.el.querySelector("input"),
            "maxlength",
            "5",
            "maxlength attribute should have been set correctly on the input"
        );
    });

    QUnit.skip("char field in editable list view", async function (assert) {
        assert.expect(6);

        const list = await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="foo" />
                </tree>
            `,
        });

        assert.containsN(
            list.el,
            "tbody td:not(.o_list_record_selector)",
            5,
            "should have 5 cells"
        );
        assert.strictEqual(
            list.el.querySelector("tbody td:not(.o_list_record_selector)").textContent,
            "yop",
            "value should be displayed properly as text"
        );

        // Edit a line and check the result
        let cell = list.el.querySelector("tbody td:not(.o_list_record_selector)");
        await click(cell);
        assert.hasClass(cell.parentElement, "o_selected_row", "should be set as edit mode");
        assert.strictEqual(
            cell.querySelector("input").value,
            "yop",
            "should have the corect value in internal input"
        );

        const input = cell.querySelector("input");
        input.value = "brolo";
        await triggerEvent(input, null, "change");

        // save
        await click(list, ".o_list_button_save");
        cell = list.el.querySelector("tbody td:not(.o_list_record_selector)");
        assert.doesNotHaveClass(
            cell.parentElement,
            "o_selected_row",
            "should not be in edit mode anymore"
        );
        assert.strictEqual(
            list.el.querySelector("tbody td:not(.o_list_record_selector)").textContent,
            "brolo",
            "value should be properly updated"
        );
    });

    QUnit.skip("char field translatable", async function (assert) {
        // assert.expect(12);
        // serverData.models.partner.fields.foo.translate = true;
        // serviceRegistry.add("localization", makeFakeLocalizationService({ multiLang: true }), { force: true });
        // const form = await makeView({
        //     type: "form",
        //     resModel: 'partner',
        //     serverData,
        //     arch: '<form string="Partners">' +
        //             '<sheet>' +
        //                 '<group>' +
        //                     '<field name="foo"/>' +
        //                 '</group>' +
        //             '</sheet>' +
        //         '</form>',
        //     resId: 1,
        //     session: {
        //         user_context: {lang: 'en_US'},
        //     },
        //     mockRPC: function (route, args) {
        //         if (route === "/web/dataset/call_button" && args.method === 'translate_fields') {
        //             assert.deepEqual(args.args, ["partner",1,"foo"], 'should call "call_button" route');
        //             return Promise.resolve({
        //                 domain: [],
        //                 context: {search_default_name: 'partnes,foo'},
        //             });
        //         }
        //         if (route === "/web/dataset/call_kw/res.lang/get_installed") {
        //             return Promise.resolve([["en_US", "English"], ["fr_BE", "French (Belgium)"]]);
        //         }
        //         if (args.method === "search_read" && args.model == "ir.translation") {
        //             return Promise.resolve([
        //                 {lang: 'en_US', src: 'yop', value: 'yop', id: 42},
        //                 {lang: 'fr_BE', src: 'yop', value: 'valeur français', id: 43}
        //             ]);
        //         }
        //         if (args.method === "write" && args.model == "ir.translation") {
        //             assert.deepEqual(args.args[1], {value: "english value"},
        //                 "the new translation value should be written");
        //             return Promise.resolve();
        //         }
        //         return this._super.apply(this, arguments);
        //     },
        // });
        // await click(form.el, ".o_form_button_edit");
        // const $button = form.$('input[type="text"].o_field_char + .o_field_translate');
        // assert.strictEqual($button.length, 1, "should have a translate button");
        // assert.strictEqual($button.text(), 'EN', 'the button should have as test the current language');
        // await click($button);
        // await nextTick();
        // assert.containsOnce($(document), '.modal', 'a translate modal should be visible');
        // assert.containsN($('.modal .o_translation_dialog'), '.translation', 2,
        //     'two rows should be visible');
        // const $enField = $('.modal .o_translation_dialog .translation:first() input');
        // assert.strictEqual($enField.val(), 'yop',
        //     'English translation should be filled');
        // assert.strictEqual($('.modal .o_translation_dialog .translation:last() input').val(), 'valeur français',
        //     'French translation should be filled');
        // $enField.value = "english value";
        // await nextTick();
        // await click($('.modal button.btn-primary'));  // save
        // await nextTick();
        // const $foo = form.$('input[type="text"].o_field_char');
        // assert.strictEqual($foo.val(), "english value",
        //     "the new translation was not transfered to modified record");
        // $foo.value = "new english value";
        // await nextTick();
        // await click($button);
        // await nextTick();
        // assert.strictEqual($('.modal .o_translation_dialog .translation:first() input').val(), 'new english value',
        //     'Modified value should be used instead of translation');
        // assert.strictEqual($('.modal .o_translation_dialog .translation:last() input').val(), 'valeur français',
        //     'French translation should be filled');
    });

    QUnit.skip("html field translatable", async function (assert) {
        // assert.expect(6);
        // serverData.models.partner.fields.foo.translate = true;
        // serviceRegistry.add("localization", makeFakeLocalizationService({ multiLang: true }), { force: true });
        // const form = await makeView({
        //     type: "form",
        //     resModel: 'partner',
        //     serverData,
        //     arch: '<form string="Partners">' +
        //             '<sheet>' +
        //                 '<group>' +
        //                     '<field name="foo"/>' +
        //                 '</group>' +
        //             '</sheet>' +
        //         '</form>',
        //     resId: 1,
        //     session: {
        //         user_context: {lang: 'en_US'},
        //     },
        //     mockRPC: function (route, args) {
        //         if (route === "/web/dataset/call_button" && args.method === 'translate_fields') {
        //             assert.deepEqual(args.args, ["partner",1,"foo"], 'should call "call_button" route');
        //             return Promise.resolve({
        //                 domain: [],
        //                 context: {
        //                     search_default_name: 'partner,foo',
        //                     translation_type: 'char',
        //                     translation_show_src: true,
        //                 },
        //             });
        //         }
        //         if (route === "/web/dataset/call_kw/res.lang/get_installed") {
        //             return Promise.resolve([["en_US", "English"], ["fr_BE", "French (Belgium)"]]);
        //         }
        //         if (args.method === "search_read" && args.model == "ir.translation") {
        //             return Promise.resolve([
        //                 {lang: 'en_US', src: 'first paragraph', value: 'first paragraph', id: 42},
        //                 {lang: 'en_US', src: 'second paragraph', value: 'second paragraph', id: 43},
        //                 {lang: 'fr_BE', src: 'first paragraph', value: 'premier paragraphe', id: 44},
        //                 {lang: 'fr_BE', src: 'second paragraph', value: 'deuxième paragraphe', id: 45},
        //             ]);
        //         }
        //         if (args.method === "write" && args.model == "ir.translation") {
        //             assert.deepEqual(args.args[1], {value: "first paragraph modified"},
        //                 "Wrong update on translation");
        //             return Promise.resolve();
        //         }
        //         return this._super.apply(this, arguments);
        //     },
        // });
        // await click(form.el, ".o_form_button_edit");
        // const $foo = form.$('input[type="text"].o_field_char');
        // // this will not affect the translate_fields effect until the record is
        // // saved but is set for consistency of the test
        // await editInput($foo, "<p>first paragraph</p><p>second paragraph</p>");
        // const $button = form.$('input[type="text"].o_field_char + .o_field_translate');
        // await click($button);
        // await nextTick();
        // assert.containsOnce($(document), '.modal', 'a translate modal should be visible');
        // assert.containsN($('.modal .o_translation_dialog'), '.translation', 4,
        //     'four rows should be visible');
        // const $enField = $('.modal .o_translation_dialog .translation:first() input');
        // assert.strictEqual($enField.val(), 'first paragraph',
        //     'first part of english translation should be filled');
        // await editInput($enField, "first paragraph modified");
        // await click($('.modal button.btn-primary'));  // save
        // await nextTick();
        // assert.strictEqual($foo.val(), "<p>first paragraph</p><p>second paragraph</p>",
        //     "the new partial translation should not be transfered");
    });

    QUnit.skip("char field translatable in create mode", async function (assert) {
        // assert.expect(1);
        // serverData.models.partner.fields.foo.translate = true;
        // serviceRegistry.add("localization", makeFakeLocalizationService({ multiLang: true }), { force: true });
        // const form = await makeView({
        //     type: "form",
        //     resModel: 'partner',
        //     serverData,
        //     arch: '<form string="Partners">' +
        //             '<sheet>' +
        //                 '<group>' +
        //                     '<field name="foo"/>' +
        //                 '</group>' +
        //             '</sheet>' +
        //         '</form>',
        // });
        // const $button = form.$('input[type="text"].o_field_char + .o_field_translate');
        // assert.strictEqual($button.length, 1, "should have a translate button in create mode");
    });

    QUnit.test("char field does not allow html injections", async function (assert) {
        assert.expect(1);

        const form = await makeView({
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
                </form>
            `,
        });

        await click(form.el, ".o_form_button_edit");
        const input = form.el.querySelector("input");
        input.value = "<script>throw Error();</script>";
        await triggerEvent(input, null, "change");

        await click(form.el, ".o_form_button_save");
        assert.strictEqual(
            form.el.querySelector(".o_field_widget").textContent,
            "<script>throw Error();</script>",
            "the value should have been properly escaped"
        );
    });

    QUnit.test("char field trim (or not) characters", async function (assert) {
        assert.expect(2);

        serverData.models.partner.fields.foo2 = { string: "Foo2", type: "char", trim: false };

        const form = await makeView({
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
                </form>
            `,
        });

        await click(form.el, ".o_form_button_edit");

        let input = form.el.querySelector("input.o_field_widget[name='foo']");
        input.value = "  abc  ";
        await triggerEvent(input, null, "change");

        input = form.el.querySelector("input.o_field_widget[name='foo2']");
        input.value = "  def  ";
        await triggerEvent(input, null, "change");

        await click(form.el, ".o_form_button_save");

        // edit mode
        await click(form.el, ".o_form_button_edit");
        assert.strictEqual(
            form.el.querySelector("input.o_field_widget[name='foo']").value,
            "abc",
            "Foo value should have been trimmed"
        );
        assert.strictEqual(
            form.el.querySelector("input.o_field_widget[name='foo2']").value,
            "  def  ",
            "Foo2 value should not have been trimmed"
        );
    });

    QUnit.skip(
        "input field: change value before pending onchange returns",
        async function (assert) {
            // assert.expect(3);
            // serverData.models.partner.onchanges = {
            //     product_id: function () {},
            // };
            // const def;
            // const form = await makeView({
            //     type: "form",
            //     resModel: 'partner',
            //     serverData,
            //     arch: '<form>' +
            //             '<sheet>' +
            //                 '<field name="p">' +
            //                     '<tree editable="bottom">' +
            //                         '<field name="product_id"/>' +
            //                         '<field name="foo"/>' +
            //                     '</tree>' +
            //                 '</field>' +
            //             '</sheet>' +
            //         '</form>',
            //     resId: 1,
            //     mockRPC: function (route, args) {
            //         const result = this._super.apply(this, arguments);
            //         if (args.method === "onchange") {
            //             return Promise.resolve(def).then(function () {
            //                 return result;
            //             });
            //         } else {
            //             return result;
            //         }
            //     },
            //     viewOptions: {
            //         mode: 'edit',
            //     },
            // });
            // await click(form.$('.o_field_x2many_list_row_add a'));
            // assert.strictEqual(form.$('input[name="foo"]').val(), 'My little Foo Value',
            //     'should contain the default value');
            // def = makeDeferred();
            // await many2one.clickOpenDropdown('product_id');
            // await many2one.clickHighlightedItem('product_id');
            // // set foo before onchange
            // await editInput(form.$('input[name="foo"]'), "tralala");
            // assert.strictEqual(form.$('input[name="foo"]').val(), 'tralala',
            //     'input should contain tralala');
            // // complete the onchange
            // def.resolve();
            // await nextTick();
            // assert.strictEqual(form.$('input[name="foo"]').val(), 'tralala',
            //     'input should contain the same value as before onchange');
        }
    );

    QUnit.skip(
        "input field: change value before pending onchange returns (with fieldDebounce)",
        async function (assert) {
            // // this test is exactly the same as the previous one, except that we set
            // // here a fieldDebounce to accurately reproduce what happens in practice:
            // // the field doesn't notify the changes on 'input', but on 'change' event.
            // assert.expect(5);
            // serverData.models.partner.onchanges = {
            //     product_id: function (obj) {
            //         obj.int_field = obj.product_id ? 7 : false;
            //     },
            // };
            // let def;
            // const form = await makeView({
            //     type: "form",
            //     resModel: 'partner',
            //     serverData,
            //     arch: `
            //         <form>
            //             <field name="p">
            //                 <tree editable="bottom">
            //                     <field name="product_id"/>
            //                     <field name="foo"/>
            //                     <field name="int_field"/>
            //                 </tree>
            //             </field>
            //         </form>`,
            //     async mockRPC(route, args) {
            //         const result = this._super(...arguments);
            //         if (args.method === "onchange") {
            //             await Promise.resolve(def);
            //         }
            //         return result;
            //     },
            //     fieldDebounce: 5000,
            // });
            // await click(form.$('.o_field_x2many_list_row_add a'));
            // assert.strictEqual(form.$('input[name="foo"]').val(), 'My little Foo Value',
            //     'should contain the default value');
            // def = makeDeferred();
            // await many2one.clickOpenDropdown('product_id');
            // await many2one.clickHighlightedItem('product_id');
            // // set foo before onchange
            // await editInput(form.$('input[name="foo"]'), "tralala");
            // assert.strictEqual(form.$('input[name="foo"]').val(), 'tralala');
            // assert.strictEqual(form.$('input[name="int_field"]').val(), '');
            // // complete the onchange
            // def.resolve();
            // await nextTick();
            // assert.strictEqual(form.$('input[name="foo"]').val(), 'tralala',
            //     'foo should contain the same value as before onchange');
            // assert.strictEqual(form.$('input[name="int_field"]').val(), '7',
            //     'int_field should contain the value returned by the onchange');
        }
    );

    QUnit.skip(
        "input field: change value before pending onchange renaming",
        async function (assert) {
            // assert.expect(3);
            // serverData.models.partner.onchanges = {
            //     product_id: function (obj) {
            //         obj.foo = 'on change value';
            //     },
            // };
            // const def = makeDeferred();
            // const form = await makeView({
            //     type: "form",
            //     resModel: 'partner',
            //     serverData,
            //     arch: '<form>' +
            //             '<sheet>' +
            //                 '<field name="product_id"/>' +
            //                 '<field name="foo"/>' +
            //             '</sheet>' +
            //         '</form>',
            //     resId: 1,
            //     mockRPC: function (route, args) {
            //         const result = this._super.apply(this, arguments);
            //         if (args.method === "onchange") {
            //             return def.then(function () {
            //                 return result;
            //             });
            //         } else {
            //             return result;
            //         }
            //     },
            //     viewOptions: {
            //         mode: 'edit',
            //     },
            // });
            // assert.strictEqual(form.$('input[name="foo"]').val(), 'yop',
            //     'should contain the correct value');
            // await many2one.clickOpenDropdown('product_id');
            // await many2one.clickHighlightedItem('product_id');
            // // set foo before onchange
            // editInput(form.$('input[name="foo"]'), "tralala");
            // assert.strictEqual(form.$('input[name="foo"]').val(), 'tralala',
            //     'input should contain tralala');
            // // complete the onchange
            // def.resolve();
            // assert.strictEqual(form.$('input[name="foo"]').val(), 'tralala',
            //     'input should contain the same value as before onchange');
        }
    );

    QUnit.skip("input field: change password value", async function (assert) {
        // assert.expect(4);
        // const form = await makeView({
        //     type: "form",
        //     resModel: 'partner',
        //     serverData,
        //     arch: '<form>' +
        //             '<field name="foo" password="True"/>' +
        //         '</form>',
        //     resId: 1,
        // });
        // assert.notEqual(form.$('.o_field_char').text(), "yop",
        //     "password field value should not be visible in read mode");
        // assert.strictEqual(form.$('.o_field_char').text(), "***",
        //     "password field value should be hidden with '*' in read mode");
        // await click(form.el, ".o_form_button_edit");
        // assert.hasAttrValue(form.$('input.o_field_char'), 'type', 'password',
        //     "password field input should be with type 'password' in edit mode");
        // assert.strictEqual(form.$('input.o_field_char').val(), 'yop',
        //     "password field input value should be the (non-hidden) password value");
    });

    QUnit.skip("input field: empty password", async function (assert) {
        // assert.expect(3);
        // serverData.models.partner.records[0].foo = false;
        // const form = await makeView({
        //     type: "form",
        //     resModel: 'partner',
        //     serverData,
        //     arch: '<form>' +
        //             '<field name="foo" password="True"/>' +
        //         '</form>',
        //     resId: 1,
        // });
        // assert.strictEqual(form.$('.o_field_char').text(), "",
        //     "password field value should be empty in read mode");
        // await click(form.el, ".o_form_button_edit");
        // assert.hasAttrValue(form.$('input.o_field_char'), 'type', 'password',
        //     "password field input should be with type 'password' in edit mode");
        // assert.strictEqual(form.$('input.o_field_char').val(), '',
        //     "password field input value should be the (non-hidden, empty) password value");
    });

    QUnit.skip(
        "input field: set and remove value, then wait for onchange",
        async function (assert) {
            // assert.expect(2);
            // serverData.models.partner.onchanges = {
            //     product_id(obj) {
            //         obj.foo = obj.product_id ? "onchange value" : false;
            //     },
            // };
            // let def;
            // const form = await makeView({
            //     type: "form",
            //     resModel: 'partner',
            //     serverData,
            //     arch: `
            //         <form>
            //             <field name="p">
            //                 <tree editable="bottom">
            //                     <field name="product_id"/>
            //                     <field name="foo"/>
            //                 </tree>
            //             </field>
            //         </form>`,
            //     async mockRPC(route, args) {
            //         const result = this._super(...arguments);
            //         if (args.method === "onchange") {
            //             await Promise.resolve(def);
            //         }
            //         return result;
            //     },
            //     fieldDebounce: 1000, // needed to accurately mock what really happens
            // });
            // await click(form.$('.o_field_x2many_list_row_add a'));
            // assert.strictEqual(form.$('input[name="foo"]').val(), "");
            // await editInput(form.$('input[name="foo"]'), "test"); // set value for foo
            // await editInput(form.$('input[name="foo"]'), ""); // remove value for foo
            // // trigger the onchange by setting a product
            // await many2one.clickOpenDropdown('product_id');
            // await many2one.clickHighlightedItem('product_id');
            // assert.strictEqual(form.$('input[name="foo"]').val(), 'onchange value',
            //     'input should contain correct value after onchange');
        }
    );
});
