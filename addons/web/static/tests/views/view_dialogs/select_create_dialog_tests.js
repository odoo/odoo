/** @odoo-module */

import {
    click,
    clickOpenedDropdownItem,
    getFixture,
    nextTick,
    editInput,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { createWebClient } from "@web/../tests/webclient/helpers";
import { browser } from "@web/core/browser/browser";
import { session } from "@web/session";
import { useSetupAction } from "@web/webclient/actions/action_hook";
import { listView } from "@web/views/list/list_view";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import {
    editFavoriteName,
    removeFacet,
    saveFavorite,
    toggleSearchBarMenu,
    toggleMenuItem,
    toggleSaveFavorite,
} from "@web/../tests/search/helpers";

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

    QUnit.module("SelectCreateDialog");

    QUnit.test(
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
                            offset: 0,
                        },
                        "should search with the complete domain (domain + search), and group by 'bar'"
                    );
                } else if (args.method === "web_search_read") {
                    if (search === 0) {
                        assert.deepEqual(
                            args.kwargs,
                            {
                                context: {
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
                                specification: { display_name: {}, foo: {} },
                                limit: 80,
                                offset: 0,
                                order: "",
                                count_limit: 10001,
                            },
                            "should search with the complete domain (domain + search)"
                        );
                    } else if (search === 1) {
                        assert.deepEqual(
                            args.kwargs,
                            {
                                context: {
                                    bin_size: true,
                                    lang: "en",
                                    tz: "taht",
                                    uid: 7,
                                }, // not part of the test, may change
                                domain: [["display_name", "like", "a"]],
                                specification: { display_name: {}, foo: {} },
                                limit: 80,
                                offset: 0,
                                order: "",
                                count_limit: 10001,
                            },
                            "should search with the domain"
                        );
                    }
                    search++;
                }
            };
            const webClient = await createWebClient({ serverData, mockRPC });
            webClient.env.services.dialog.add(SelectCreateDialog, {
                noCreate: true,
                resModel: "partner",
                domain: [["display_name", "like", "a"]],
                context: {
                    search_default_groupby_bar: true,
                    search_default_foo: "piou",
                },
            });
            await nextTick();
            await removeFacet(target.querySelector(".modal"), "Bar");
            await removeFacet(target.querySelector(".modal"));
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

    QUnit.test("SelectCreateDialog cascade x2many in create mode", async function (assert) {
        assert.expect(5);

        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });

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
            "badassery,false,list": `<tree><field name="level"/></tree>`,
            "badassery,false,search": `<search><field name="level"/></search>`,
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
                if (route === "/web/dataset/call_kw/instrument/web_save") {
                    assert.deepEqual(
                        args.args[1],
                        { badassery: [[4, 1]], name: "ABC" },
                        "The method create should have been called with the right arguments"
                    );
                    return [{ id: 90 }];
                }
            },
        });

        await click(target, ".o_field_x2many_list_row_add a");

        await editInput(target, ".o_field_widget[name=instrument] input", "ABC");
        await clickOpenedDropdownItem(target, "instrument", "Create and edit...");

        assert.containsOnce(target, ".modal .modal-lg");

        await click(target.querySelector(".modal .o_field_x2many_list_row_add a"));

        assert.containsN(target, ".modal .modal-lg", 2);

        await click(target.querySelector(".modal .o_data_row input[type=checkbox]"));
        await nextTick(); // wait for the select button to be enabled
        await click(target.querySelector(".modal .o_select_button"));

        assert.containsOnce(target, ".modal .modal-lg");
        assert.strictEqual(target.querySelector(".modal .o_data_cell").innerText, "Awsome");

        await click(target.querySelector(".modal .o_form_button_save"));
    });

    QUnit.test("SelectCreateDialog: save current search", async function (assert) {
        assert.expect(5);

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

        patchWithCleanup(listView.Controller.prototype, {
            setup() {
                super.setup(...arguments);
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
            if (args.method === "get_views") {
                assert.equal(args.kwargs.options.load_filters, true, "Missing load_filters option");
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
        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "Bar");

        assert.containsN(target, ".o_data_row", 2, "should contain 2 records");

        // save filter
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
                    assert.equal(records.join(","), "1,2,3");
                },
            });
            await nextTick();

            await click(target, "thead .o_list_record_selector input");
            await click(target, ".o_list_selection_box .o_list_select_domain");
            await click(target, ".modal .o_select_button");
        }
    );

    QUnit.test(
        "SelectCreateDialog calls on_selected with every record matching without selecting a domain",
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
                    assert.equal(records.join(","), "1,2");
                },
            });

            await nextTick();

            await click(target, "thead .o_list_record_selector input");
            await click(target, ".o_list_selection_box");
            await click(target, ".modal .o_select_button");
        }
    );

    QUnit.test("SelectCreateDialog: default props, create a record", async function (assert) {
        serverData.views = {
            "partner,false,list": `<tree><field name="display_name"/></tree>`,
            "partner,false,search": `
                <search>
                    <filter name="bar" help="Bar" domain="[('bar', '=', True)]"/>
                </search>`,
            "partner,false,form": `<form><field name="display_name"/></form>`,
        };

        const webClient = await createWebClient({ serverData });

        webClient.env.services.dialog.add(SelectCreateDialog, {
            onSelected: (resIds) => assert.step(`onSelected ${resIds}`),
            resModel: "partner",
        });
        await nextTick();

        assert.containsOnce(target, ".o_dialog");
        assert.containsN(target, ".o_dialog .o_list_view .o_data_row", 3);
        assert.containsN(target, ".o_dialog footer button", 3);
        assert.containsOnce(target, ".o_dialog footer button.o_select_button");
        assert.containsOnce(target, ".o_dialog footer button.o_create_button");
        assert.containsOnce(target, ".o_dialog footer button.o_form_button_cancel");

        await click(target.querySelector(".o_dialog footer button.o_create_button"));

        assert.containsN(target, ".o_dialog", 2);
        assert.containsOnce(target, ".o_dialog .o_form_view");

        await editInput(target, ".o_dialog .o_form_view .o_field_widget input", "hello");
        await click(target.querySelector(".o_dialog .o_form_button_save"));

        assert.containsNone(target, ".o_dialog");
        assert.verifySteps(["onSelected 4"]);
    });
});
