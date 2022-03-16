/** @odoo-module */

import { click, getFixture, nextTick, triggerHotkey } from "@web/../tests/helpers/utils";
import { makeView } from "@web/../tests/views/helpers";
import { createWebClient } from "@web/../tests/webclient/helpers";
import { dialogService } from "@web/core/dialog/dialog_service";
import { registry } from "@web/core/registry";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { setupControlPanelServiceRegistry } from "@web/../tests/search/helpers";

const serviceRegistry = registry.category("services");

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
        setupControlPanelServiceRegistry();
        serviceRegistry.add("dialog", dialogService);
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
            ".modal-footer button",
            "should have only one button in footer"
        );
    });

    QUnit.skipWOWL("formviewdialog buttons in footer are not duplicated", async function (assert) {
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
                        <footer><button string="Custom Button" type="object" class="btn-primary"/></footer>
                    </form>
                `,
        };
        const webClient = await createWebClient({ serverData });

        webClient.env.services.dialog.add(FormViewDialog, {
            resModel: "partner",
            resId: 1,
        });

        await nextTick();

        assert.containsOnce(target, ".modal button.btn-primary", "should have 1 buttons in modal");

        await click(target, ".o_field_x2many_list_row_add a");
        triggerHotkey("escape");
        await nextTick();

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
        serverData.views = {
            "instrument,false,form": `
                        <form>
                            <field name="name"/>
                            <field name="badassery" context="{'tree_view_ref': 'some_other_tree_view'}"/>
                        </form>`,
            "badassery,false,list": `
                        <tree>
                            <field name="level"/>
                        </tree>`,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `<form>
                    <field name="name"/>
                    <field name="instrument" context="{'tree_view_ref': 'some_tree_view'}"/>
                   </form>`,
            mockRPC: function (route, args) {
                if (args.method === "get_formview_id") {
                    return Promise.resolve(false);
                }
                if (args.method === "load_views" && args.model === "instrument") {
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
                if (args.method === "load_views" && args.model === "badassery") {
                    assert.deepEqual(
                        args.kwargs.context,
                        {
                            base_model_name: "instrument",
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
        await click(target, ".o_form_button_edit");
        await click(target, '.o_field_widget[name="instrument"] button.o_external_button');
    });

    // We are not sure about the behaviour of this test.
    // It seems that the first record uses 1 context and the next ones uses a different one.
    // This is confusing and maybe wrong.
    QUnit.skipWOWL(
        "Form dialog replaces the context with _createContext method when specified",
        async function (assert) {
            assert.expect(5);
            serverData.views = {
                "partner,false,form": `
                        <form string="Partner">
                            <sheet>
                                <group><field name="foo"/></group>
                            </sheet>
                        </form>
                `,
            };

            const mockRPC = async function (route, args) {
                if (args.method === "create") {
                    assert.step(JSON.stringify(args.kwargs.context));
                }
            };
            const webClient = await createWebClient({ serverData, mockRPC });

            webClient.env.services.dialog.add(FormViewDialog, {
                resModel: "partner",
                context: { answer: 42 },
                _createContext: () => ({ dolphin: 64 }),
            });

            await nextTick();

            assert.containsNone(target, ".modal-body button", "should not have any button in body");
            assert.containsN(target, ".modal-footer button", 3, "should have 3 buttons in footer");

            await click(target, ".modal-footer .o_fvd_button_save_new");
            await click(target, ".modal-footer .o_fvd_button_save_new");

            assert.verifySteps([
                '{"lang":"en","uid":7,"tz":"taht","answer":42}',
                '{"lang":"en","uid":7,"tz":"taht","dolphin":64}',
            ]);
        }
    );

    QUnit.test("Form dialog keeps full context between created records", async function (assert) {
        assert.expect(5);

        serverData.views = {
            "partner,false,form": `
                    <form string="Partner">
                        <sheet>
                            <group><field name="foo"/></group>
                        </sheet>
                    </form>
            `,
        };
        const mockRPC = async function (route, args) {
            if (args.method === "create") {
                assert.step(JSON.stringify(args.kwargs.context));
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        webClient.env.services.dialog.add(FormViewDialog, {
            resModel: "partner",
            context: { answer: 42 },
        });

        await nextTick();

        assert.containsNone(target, ".modal-body button", "should not have any button in body");
        assert.containsN(target, ".modal-footer button", 3, "should have 3 buttons in footer");

        await click(target, ".modal-footer .o_form_button_save_new");
        await click(target, ".modal-footer .o_form_button_save_new");

        assert.verifySteps([
            '{"lang":"en","uid":7,"tz":"taht","answer":42}',
            '{"lang":"en","uid":7,"tz":"taht","answer":42}',
        ]);
    });

    QUnit.skipWOWL("propagate can_create onto the search popup o2m", async function (assert) {
        serverData.models.instrument.records = [
            { id: 1, name: "Tromblon1" },
            { id: 2, name: "Tromblon2" },
            { id: 3, name: "Tromblon3" },
            { id: 4, name: "Tromblon4" },
            { id: 5, name: "Tromblon5" },
            { id: 6, name: "Tromblon6" },
            { id: 7, name: "Tromblon7" },
            { id: 8, name: "Tromblon8" },
        ];
        serverData.views = {
            "instrument,false,list": `
                    <tree>
                        <field name="name"/>
                    </tree>
                `,
            "instrument,false,search": `
                    <search>
                        <field name="name"/>
                    </search>
                `,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="name"/>
                    <field name="instrument" can_create="false"/>
                </form>
            `,
            mockRPC: function (route, args) {
                if (args.method === "get_formview_id") {
                    return Promise.resolve(false);
                }
            },
        });

        await click(target, ".o_form_button_edit");

        // await new Promise(() => {});

        // await testUtils.fields.many2one.clickOpenDropdown("instrument");

        // assert.containsNone(target, ".ui-autocomplete a:contains(Start typing...)");

        // await testUtils.fields.editInput(
        //     form.el.querySelector(".o_field_many2one[name=instrument] input"),
        //     "a"
        // );

        // assert.containsNone(target, ".ui-autocomplete a:contains(Create and Edit)");

        // await testUtils.fields.editInput(
        //     form.el.querySelector(".o_field_many2one[name=instrument] input"),
        //     ""
        // );
        // await testUtils.fields.many2one.clickItem("instrument", "Search More...");

        // var $modal = $(".modal-dialog.modal-lg");

        // assert.strictEqual($modal.length, 1, "Modal present");

        // assert.strictEqual(
        //     $modal.find(".modal-footer button").text(),
        //     "Cancel",
        //     "Only the cancel button is present in modal"
        // );
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
            const webClient = await createWebClient({ serverData });
            webClient.env.services.dialog.add(FormViewDialog, {
                resModel: "partner",
                context: { answer: 42 },
                save: () => {
                    return reject ? Promise.reject() : Promise.resolve();
                },
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
});
