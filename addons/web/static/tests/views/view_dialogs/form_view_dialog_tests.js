/** @odoo-module */

import {
    click,
    editInput,
    getFixture,
    nextTick,
    patchWithCleanup,
    triggerHotkey,
    makeDeferred,
} from "@web/../tests/helpers/utils";
import { makeViewInDialog, setupViewRegistries } from "@web/../tests/views/helpers";
import { createWebClient } from "@web/../tests/webclient/helpers";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

QUnit.module("ViewDialogs", (hooks) => {
    let serverData;
    let target;

    hooks.beforeEach(async () => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        foo: { string: "Foo", type: "char" },
                        bar: { string: "Bar", type: "boolean" },
                        instrument: {
                            string: "Instruments",
                            type: "many2one",
                            relation: "instrument",
                        },
                    },
                    records: [
                        { id: 1, foo: "blip", display_name: "blipblip", bar: true },
                        { id: 2, foo: "ta tata ta ta", display_name: "macgyver", bar: false },
                        { id: 3, foo: "piou piou", display_name: "Jack O'Neill", bar: true },
                    ],
                },
                instrument: {
                    fields: {
                        name: { string: "name", type: "char" },
                        badassery: {
                            string: "level",
                            type: "many2many",
                            relation: "badassery",
                            domain: [["level", "=", "Awsome"]],
                        },
                    },
                },

                badassery: {
                    fields: {
                        level: { string: "level", type: "char" },
                    },
                    records: [{ id: 1, level: "Awsome" }],
                },

                product: {
                    fields: {
                        name: { string: "name", type: "char" },
                        partner: { string: "Doors", type: "one2many", relation: "partner" },
                    },
                    records: [{ id: 1, name: "The end" }],
                },
            },
        };
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.module("FormViewDialog");

    QUnit.test("formviewdialog buttons in footer are positioned properly", async function (assert) {
        serverData.views = {
            "partner,false,form": `
                    <form string="Partner">
                        <sheet>
                            <group>
                                <field name="foo"/>
                            </group>
                            <footer>
                                <button string="Custom Button" type="object" class="btn-primary"/>
                            </footer>
                        </sheet>
                    </form>
                `,
        };
        const webClient = await createWebClient({ serverData });
        webClient.env.services.dialog.add(FormViewDialog, {
            resModel: "partner",
            resId: 1,
        });

        await nextTick();

        assert.containsNone(target, ".modal-body button", "should not have any button in body");
        assert.containsOnce(
            target,
            ".modal-footer button:not(.d-none)",
            "should have only one button in footer"
        );
    });

    QUnit.test("modifiers are considered on multiple <footer/> tags", async function (assert) {
        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="bar"/>
                    <footer invisible="not bar">
                        <button>Hello</button>
                        <button>World</button>
                    </footer>
                    <footer invisible="bar">
                        <button>Foo</button>
                    </footer>
                </form>`,
        };
        const webClient = await createWebClient({ serverData });
        webClient.env.services.dialog.add(FormViewDialog, {
            resModel: "partner",
            resId: 1,
        });

        await nextTick();

        assert.deepEqual(
            getVisibleButtonTexts(),
            ["Hello", "World"],
            "only the first button section should be visible"
        );

        await click(target.querySelector(".o_field_boolean input"));

        assert.deepEqual(
            getVisibleButtonTexts(),
            ["Foo"],
            "only the second button section should be visible"
        );

        function getVisibleButtonTexts() {
            return [...target.querySelectorAll(".modal-footer button:not(.d-none)")].map((x) =>
                x.innerHTML.trim()
            );
        }
    });

    QUnit.test("formviewdialog buttons in footer are not duplicated", async function (assert) {
        serverData.models.partner.fields.poney_ids = {
            string: "Poneys",
            type: "one2many",
            relation: "partner",
        };
        serverData.models.partner.records[0].poney_ids = [];
        serverData.views = {
            "partner,false,form": `
                    <form string="Partner">
                        <field name="poney_ids"><tree editable="top"><field name="display_name"/></tree></field>
                        <footer><button string="Custom Button" type="object" class="my_button"/></footer>
                    </form>
                `,
        };
        const webClient = await createWebClient({ serverData });

        webClient.env.services.dialog.add(FormViewDialog, {
            resModel: "partner",
            resId: 1,
        });
        await nextTick();

        assert.containsOnce(target, ".modal");
        assert.containsOnce(target, ".modal button.my_button", "should have 1 buttons in modal");

        await click(target, ".o_field_x2many_list_row_add a");
        triggerHotkey("escape");
        await nextTick();

        assert.containsOnce(target, ".modal");
        assert.containsOnce(
            target,
            ".modal button.btn-primary",
            "should still have 1 buttons in modal"
        );
    });

    QUnit.test("Form dialog and subview with _view_ref contexts", async function (assert) {
        assert.expect(2);

        serverData.models.instrument.records = [{ id: 1, name: "Tromblon", badassery: [1] }];
        serverData.models.partner.records[0].instrument = 1;
        // This is an old test, written before "get_views" (formerly "load_views") automatically
        // inlines x2many subviews. As the purpose of this test is to assert that the js fetches
        // the correct sub view when it is not inline (which can still happen in nested form views),
        // we bypass the inline mecanism of "get_views" by setting widget="many2many" on the field.
        serverData.views = {
            "instrument,false,form": `
                        <form>
                            <field name="name"/>
                            <field name="badassery" widget="many2many" context="{'tree_view_ref': 'some_other_tree_view'}"/>
                        </form>`,
            "badassery,false,list": `
                        <tree>
                            <field name="level"/>
                        </tree>`,
        };

        await makeViewInDialog({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="name"/>
                    <field name="instrument" context="{'tree_view_ref': 'some_tree_view'}"/>
                </form>`,
            mockRPC: function (route, args) {
                if (args.method === "get_formview_id") {
                    return Promise.resolve(false);
                }
                if (args.method === "get_views" && args.model === "instrument") {
                    assert.deepEqual(
                        args.kwargs.context,
                        {
                            lang: "en",
                            tree_view_ref: "some_tree_view",
                            tz: "taht",
                            uid: 7,
                        },
                        "1 The correct _view_ref should have been sent to the server, first time"
                    );
                }
                if (args.method === "get_views" && args.model === "badassery") {
                    assert.deepEqual(
                        args.kwargs.context,
                        {
                            lang: "en",
                            tree_view_ref: "some_other_tree_view",
                            tz: "taht",
                            uid: 7,
                        },
                        "2 The correct _view_ref should have been sent to the server for the subview"
                    );
                }
            },
        });
        await click(target, '.o_field_widget[name="instrument"] button.o_external_button');
    });

    QUnit.test("click on view buttons in a FormViewDialog", async function (assert) {
        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="foo"/>
                    <button name="method1" type="object" string="Button 1" class="btn1"/>
                    <button name="method2" type="object" string="Button 2" class="btn2" close="1"/>
                </form>`,
        };

        function mockRPC(route, args) {
            assert.step(args.method || route);
        }
        const webClient = await createWebClient({ serverData, mockRPC });
        patchWithCleanup(webClient.env.services.action, {
            doActionButton: (params) => {
                assert.step(params.name);
                params.onClose();
            },
        });
        webClient.env.services.dialog.add(FormViewDialog, {
            resModel: "partner",
            resId: 1,
        });
        await nextTick();

        assert.containsOnce(target, ".o_dialog .o_form_view");
        assert.containsN(target, ".o_dialog .o_form_view button", 2);
        assert.verifySteps(["/web/webclient/load_menus", "get_views", "web_read"]);
        await click(target.querySelector(".o_dialog .o_form_view .btn1"));
        assert.containsOnce(target, ".o_dialog .o_form_view");
        assert.verifySteps(["method1", "web_read"]); // should re-read the record
        await click(target.querySelector(".o_dialog .o_form_view .btn2"));
        assert.containsNone(target, ".o_dialog .o_form_view");
        assert.verifySteps(["method2"]); // should not read as we closed
    });

    QUnit.test(
        "formviewdialog is not closed when button handlers return a rejected promise",
        async function (assert) {
            serverData.views = {
                "partner,false,form": `
                        <form string="Partner">
                            <sheet>
                                <group><field name="foo"/></group>
                            </sheet>
                        </form>
                `,
            };
            let reject = true;
            function mockRPC(route, args) {
                if (args.method === "web_save" && reject) {
                    return Promise.reject();
                }
            }
            const webClient = await createWebClient({ serverData, mockRPC });
            webClient.env.services.dialog.add(FormViewDialog, {
                resModel: "partner",
                context: { answer: 42 },
            });

            await nextTick();

            assert.containsNone(target, ".modal-body button", "should not have any button in body");
            assert.containsN(target, ".modal-footer button", 3, "should have 3 buttons in footer");

            await click(target, ".modal .o_form_button_save");
            assert.containsOnce(target, ".modal", "modal should still be opened");

            reject = false;
            await click(target, ".modal .o_form_button_save");
            assert.containsNone(target, ".modal", "modal should be closed");
        }
    );

    QUnit.test("FormViewDialog with remove button", async function (assert) {
        serverData.views = {
            "partner,false,form": `<form><field name="foo"/></form>`,
        };

        const webClient = await createWebClient({ serverData });
        webClient.env.services.dialog.add(FormViewDialog, {
            resModel: "partner",
            resId: 1,
            removeRecord: () => assert.step("remove"),
        });
        await nextTick();

        assert.containsOnce(target, ".o_dialog .o_form_view");
        assert.containsOnce(target, ".o_dialog .modal-footer .o_form_button_remove");
        await click(target.querySelector(".o_dialog .modal-footer .o_form_button_remove"));
        assert.verifySteps(["remove"]);
        assert.containsNone(target, ".o_dialog .o_form_view");
    });

    QUnit.test("Buttons are set as disabled on click", async function (assert) {
        serverData.views = {
            "partner,false,form": `
                    <form string="Partner">
                        <sheet>
                            <group>
                                <field name="name"/>
                            </group>
                        </sheet>
                    </form>
                `,
        };
        const def = makeDeferred();
        async function mockRPC(route, args) {
            if (args.method === "web_save") {
                await def;
            }
        }
        const webClient = await createWebClient({ serverData, mockRPC });
        webClient.env.services.dialog.add(FormViewDialog, {
            resModel: "partner",
            resId: 1,
        });

        await nextTick();
        await editInput(
            target.querySelector(".o_dialog .o_content .o_field_char .o_input"),
            "",
            "test"
        );

        await click(target.querySelector(".o_dialog .modal-footer .o_form_button_save"));
        assert.strictEqual(
            target
                .querySelector(".o_dialog .modal-footer .o_form_button_save")
                .getAttribute("disabled"),
            "1"
        );

        def.resolve();
        await nextTick();
        assert.containsNone(target, ".o_dialog .o_form_view");
    });

    QUnit.test("FormViewDialog with discard button", async function (assert) {
        serverData.views = {
            "partner,false,form": `<form><field name="foo"/></form>`,
        };

        const webClient = await createWebClient({ serverData });
        webClient.env.services.dialog.add(FormViewDialog, {
            resModel: "partner",
            resId: 1,
            onRecordDiscarded: () => assert.step("discard"),
        });
        await nextTick();

        assert.containsOnce(target, ".o_dialog .o_form_view");
        assert.containsOnce(target, ".o_dialog .modal-footer .o_form_button_cancel");
        await click(target.querySelector(".o_dialog .modal-footer .o_form_button_cancel"));
        assert.verifySteps(["discard"]);
        assert.containsNone(target, ".o_dialog .o_form_view");

        webClient.env.services.dialog.add(FormViewDialog, {
            resModel: "partner",
            resId: 1,
            onRecordDiscarded: () => assert.step("discard"),
        });
        await nextTick();

        assert.containsOnce(target, ".o_dialog .o_form_view");
        await click(target.querySelector(".o_dialog .btn-close"));
        assert.verifySteps(["discard"]);
        assert.containsNone(target, ".o_dialog .o_form_view");
    });
});
