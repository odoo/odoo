/** @odoo-module */

import {
    click,
    getFixture,
    nextTick,
    patchWithCleanup,
    triggerHotkey,
} from "@web/../tests/helpers/utils";
import { makeView } from "@web/../tests/views/helpers";
import { createWebClient } from "@web/../tests/webclient/helpers";
import { browser } from "@web/core/browser/browser";
import { dialogService } from "@web/core/dialog/dialog_service";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { useSetupAction } from "@web/webclient/actions/action_hook";
import { ListView } from "@web/views/list/list_view";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import {
    editFavoriteName,
    removeFacet,
    saveFavorite,
    setupControlPanelServiceRegistry,
    toggleFavoriteMenu,
    toggleFilterMenu,
    toggleMenuItem,
    toggleSaveFavorite,
} from "../search/helpers";

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

    QUnit.module("SelectCreateDialog");

    QUnit.skipWOWL(
        "SelectCreateDialog use domain, group_by and search default",
        async function (assert) {
            assert.expect(3);

            serverData.views = {
                "partner,false,list": `
                    <tree string="Partner">
                        <field name="display_name"/>
                        <field name="foo"/>
                    </tree>
                    `,
                "partner,false,search": `
                    <search>
                        <field name="foo" filter_domain="[('display_name','ilike',self), ('foo','ilike',self)]"/>
                        <group expand="0" string="Group By">
                            <filter name="groupby_bar" context="{'group_by' : 'bar'}"/>
                        </group>
                    </search>
                    `,
            };
            let search = 0;
            const mockRPC = async (route, args) => {
                if (args.method === "web_read_group") {
                    assert.deepEqual(
                        args.kwargs,
                        {
                            context: {
                                lang: "en",
                                tz: "taht",
                                uid: 7,
                                search_default_foo: "piou",
                                search_default_groupby_bar: true,
                            },
                            domain: [
                                "&",
                                ["display_name", "like", "a"],
                                "&",
                                ["display_name", "ilike", "piou"],
                                ["foo", "ilike", "piou"],
                            ],
                            fields: ["display_name", "foo", "bar"],
                            groupby: ["bar"],
                            orderby: "",
                            lazy: true,
                            limit: 80,
                        },
                        "should search with the complete domain (domain + search), and group by 'bar'"
                    );
                }
                if (search === 0 && args.method === "web_search_read") {
                    assert.deepEqual(
                        args.kwargs,
                        {
                            context: {
                                search_default_foo: "piou",
                                search_default_groupby_bar: true,
                                bin_size: true,
                                lang: "en",
                                tz: "taht",
                                uid: 7,
                            }, // not part of the test, may change
                            domain: [
                                "&",
                                ["display_name", "like", "a"],
                                "&",
                                ["display_name", "ilike", "piou"],
                                ["foo", "ilike", "piou"],
                            ],
                            fields: ["display_name", "foo"],
                            model: "partner",
                            limit: 80,
                            sort: "",
                        },
                        "should search with the complete domain (domain + search)"
                    );
                } else if (search === 1 && args.method === "web_search_read") {
                    assert.deepEqual(
                        args.kwargs,
                        {
                            context: {
                                search_default_foo: "piou",
                                search_default_groupby_bar: true,
                                bin_size: true,
                                lang: "en",
                                tz: "taht",
                                uid: 7,
                            }, // not part of the test, may change
                            domain: [["display_name", "like", "a"]],
                            fields: ["display_name", "foo"],
                            model: "partner",
                            limit: 80,
                            sort: "",
                        },
                        "should search with the domain"
                    );
                }
            };
            const webClient = await createWebClient({ serverData, mockRPC });
            webClient.env.services.dialog.add(SelectCreateDialog, {
                noCreate: true,
                readonly: true, //Not used
                resModel: "partner",
                domain: [["display_name", "like", "a"]],
                context: {
                    search_default_groupby_bar: true,
                    search_default_foo: "piou",
                },
            });
            await nextTick();
            const modal = target.querySelector(".modal");
            removeFacet(modal, "Bar");
            removeFacet(modal);
        }
    );

    QUnit.test("SelectCreateDialog correctly evaluates domains", async function (assert) {
        assert.expect(1);

        serverData.views = {
            "partner,false,list": `
                    <tree string="Partner">
                        <field name="display_name"/>
                        <field name="foo"/>
                    </tree>
                `,
            "partner,false,search": `
                    <search>
                        <field name="foo"/>
                    </search>
                `,
        };
        const mockRPC = async (route, args) => {
            if (args.method === "web_search_read") {
                assert.deepEqual(
                    args.kwargs.domain,
                    [["id", "=", 2]],
                    "should have correctly evaluated the domain"
                );
            }
        };
        patchWithCleanup(session.user_context, { uid: 2 });
        const webClient = await createWebClient({ serverData, mockRPC });
        webClient.env.services.dialog.add(SelectCreateDialog, {
            noCreate: true,
            readonly: true, //Not used
            resModel: "partner",
            domain: [["id", "=", session.user_context.uid]],
        });
        await nextTick();
    });

    QUnit.test("SelectCreateDialog list view in readonly", async function (assert) {
        serverData.views = {
            "partner,false,list": `
                    <tree string="Partner" editable="bottom">
                        <field name="display_name"/>
                        <field name="foo"/>
                    </tree>
                `,
            "partner,false,search": `
                    <search/>
                `,
        };
        const webClient = await createWebClient({ serverData });
        webClient.env.services.dialog.add(SelectCreateDialog, {
            resModel: "partner",
        });

        await nextTick();

        // click on the first row to see if the list is editable
        target.querySelectorAll(".o_list_view tbody tr td")[1].click();
        await nextTick();
        assert.equal(
            target.querySelectorAll(".o_list_view tbody tr td .o_field_char input").length,
            0,
            "list view should not be editable in a SelectCreateDialog"
        );
    });

    QUnit.skipWOWL("SelectCreateDialog cascade x2many in create mode", async function (assert) {
        assert.expect(5);
        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="name"/>
                    <field name="instrument" widget="one2many" mode="tree"/>
                </form>
            `,

            "instrument,false,form": `
                <form>
                    <field name="name"/>
                    <field name="badassery">
                        <tree>
                            <field name="level"/>
                        </tree>
                    </field>
                </form>
            `,

            "badassery,false,list": `
                <tree>
                    <field name="level"/>
                </tree>
            `,

            "badassery,false,search": `
                <search>
                    <field name="level"/>
                </search>
            `,
        };

        await makeView({
            type: "form",
            resModel: "product",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="name"/>
                    <field name="partner" widget="one2many" >
                        <tree editable="top">
                            <field name="display_name"/>
                            <field name="instrument"/>
                        </tree>
                    </field>
                </form>
            `,
            mockRPC: (route, args) => {
                if (route === "/web/dataset/call_kw/partner/get_formview_id") {
                    return Promise.resolve(false);
                }
                if (route === "/web/dataset/call_kw/instrument/get_formview_id") {
                    return Promise.resolve(false);
                }
                if (route === "/web/dataset/call_kw/instrument/create") {
                    assert.deepEqual(
                        args.args,
                        [{ badassery: [[6, false, [1]]], name: "ABC" }],
                        "The method create should have been called with the right arguments"
                    );
                    return Promise.resolve(false);
                }
            },
        });

        await click(target, ".o_form_button_edit");
        await click(target, ".o_field_x2many_list_row_add a");

        // await testUtils.fields.many2one.createAndEdit("instrument");

        // var $modal = $(".modal-lg");

        // assert.equal($modal.length, 1, "There should be one modal");

        // await testUtils.dom.click($modal.find(".o_field_x2many_list_row_add a"));

        // var $modals = $(".modal-lg");

        // assert.equal($modals.length, 2, "There should be two modals");

        // var $second_modal = $modals.not($modal);
        // await testUtils.dom.click(
        //     $second_modal.find(
        //         ".o_list_table.table.table-sm.table-striped.o_list_table_ungrouped .o_data_row input[type=checkbox]"
        //     )
        // );

        // await testUtils.dom.click($second_modal.find(".o_select_button"));

        // $modal = $(".modal-lg");

        // assert.equal($modal.length, 1, "There should be one modal");

        // assert.equal(
        //     $modal.find(".o_data_cell").text(),
        //     "Awsome",
        //     "There should be one item in the list of the modal"
        // );

        // await testUtils.dom.click($modal.find(".btn.btn-primary"));
    });

    QUnit.test("SelectCreateDialog: save current search", async function (assert) {
        assert.expect(4);

        serverData.views = {
            "partner,false,list": `
                <tree>
                    <field name="display_name"/>
                </tree>
            `,
            "partner,false,search": `
                <search>
                    <filter name="bar" help="Bar" domain="[('bar', '=', True)]"/>
                </search>
            `,
        };

        patchWithCleanup(ListView.prototype, {
            setup() {
                this._super(...arguments);
                useSetupAction({
                    getContext: () => ({ shouldBeInFilterContext: true }),
                });
            },
        });

        const mockRPC = (_, args) => {
            if (args.model === "ir.filters" && args.method === "create_or_replace") {
                const irFilter = args.args[0];
                assert.deepEqual(
                    irFilter.domain,
                    `[("bar", "=", True)]`,
                    "should save the correct domain"
                );
                const expectedContext = {
                    group_by: [], // default groupby is an empty list
                    shouldBeInFilterContext: true,
                };
                assert.deepEqual(
                    irFilter.context,
                    expectedContext,
                    "should save the correct context"
                );
                return 7; // fake serverSideId
            }
        };
        patchWithCleanup(browser, { setTimeout: (fn) => fn() });
        const webClient = await createWebClient({ serverData, mockRPC });

        webClient.env.services.dialog.add(SelectCreateDialog, {
            context: { shouldNotBeInFilterContext: false },
            resModel: "partner",
        });
        await nextTick();

        assert.containsN(target, ".o_data_row", 3, "should contain 3 records");

        // filter on bar
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "Bar");

        assert.containsN(target, ".o_data_row", 2, "should contain 2 records");

        // save filter
        await toggleFavoriteMenu(target);
        await toggleSaveFavorite(target);
        await editFavoriteName(target, "some name");
        await saveFavorite(target);
    });

    QUnit.test(
        "SelectCreateDialog calls on_selected with every record matching the domain",
        async function (assert) {
            assert.expect(1);
            serverData.views = {
                "partner,false,list": `
                        <tree limit="2" string="Partner">
                            <field name="display_name"/>
                            <field name="foo"/>
                        </tree>
                    `,
                "partner,false,search": `
                        <search>
                            <field name="foo"/>
                        </search>
                    `,
            };

            const webClient = await createWebClient({ serverData });
            webClient.env.services.dialog.add(SelectCreateDialog, {
                resModel: "partner",
                onSelected: function (records) {
                    assert.equal(records.length, 3);
                },
            });
            await nextTick();

            await click(target, "thead .o_list_record_selector input");
            await click(target, ".o_list_selection_box .o_list_select_domain");
            await click(target, ".modal .o_select_button");
        }
    );
});
