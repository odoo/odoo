/** @odoo-module **/

import { AddToBoard } from "@board/add_to_board/add_to_board";
import {
    click,
    getFixture,
    patchWithCleanup,
    mouseEnter,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import {
    applyFilter,
    applyGroup,
    editConditionValue,
    toggleAddCustomFilter,
    toggleAddCustomGroup,
    toggleComparisonMenu,
    toggleFavoriteMenu,
    toggleFilterMenu,
    toggleGroupByMenu,
    toggleMenuItem,
    toggleMenuItemOption,
} from "@web/../tests/search/helpers";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import LegacyAddToBoard from "board.AddToBoardMenu";
import LegacyFavoriteMenu from "web.FavoriteMenu";
import testUtils from "web.test_utils";
import { makeFakeUserService } from "@web/../tests/helpers/mock_services";

const patchDate = testUtils.mock.patchDate;
const favoriteMenuRegistry = registry.category("favoriteMenu");

let serverData;
let target;

QUnit.module("Board", (hooks) => {
    hooks.beforeEach(() => {
        const models = {
            board: {
                fields: {},
                records: [],
            },
            partner: {
                fields: {
                    display_name: { string: "Displayed name", type: "char", searchable: true },
                    foo: {
                        string: "Foo",
                        type: "char",
                        default: "My little Foo Value",
                        searchable: true,
                    },
                    bar: { string: "Bar", type: "boolean" },
                    int_field: {
                        string: "Integer field",
                        type: "integer",
                        group_operator: "sum",
                    },
                },
                records: [
                    {
                        id: 1,
                        display_name: "first record",
                        foo: "yop",
                        int_field: 3,
                    },
                    {
                        id: 2,
                        display_name: "second record",
                        foo: "lalala",
                        int_field: 5,
                    },
                    {
                        id: 4,
                        display_name: "aaa",
                        foo: "abc",
                        int_field: 2,
                    },
                ],
            },
        };

        LegacyFavoriteMenu.registry.add("add-to-board-menu", LegacyAddToBoard, 10);
        favoriteMenuRegistry.add(
            "add-to-board",
            {
                Component: AddToBoard,
                groupNumber: 4,
                isDisplayed: ({ config }) => config.actionType === "ir.actions.act_window",
            },
            { sequence: 10 }
        );
        serverData = { models };
        target = getFixture();
    });

    QUnit.module("Add to dashboard");

    QUnit.test("save actions to dashboard", async function (assert) {
        assert.expect(6);

        serverData.models.partner.fields.foo.sortable = true;

        serverData.views = {
            "partner,false,list": '<list><field name="foo"/></list>',
            "partner,false,search": "<search></search>",
        };
        patchWithCleanup(browser, { setTimeout: (fn) => fn() });

        const mockRPC = (route, args) => {
            if (route === "/board/add_to_dashboard") {
                assert.deepEqual(
                    args.context_to_save.group_by,
                    ["foo"],
                    "The group_by should have been saved"
                );
                assert.deepEqual(
                    args.context_to_save.orderedBy,
                    [
                        {
                            name: "foo",
                            asc: true,
                        },
                    ],
                    "The orderedBy should have been saved"
                );
                assert.strictEqual(
                    args.context_to_save.fire,
                    "on the bayou",
                    "The context of a controller should be passed and flattened"
                );
                assert.strictEqual(args.action_id, 1, "should save the correct action");
                assert.strictEqual(args.view_mode, "list", "should save the correct view type");
                return Promise.resolve(true);
            }
        };

        const webClient = await createWebClient({ serverData, mockRPC });

        await doAction(webClient, {
            id: 1,
            res_model: "partner",
            type: "ir.actions.act_window",
            context: { fire: "on the bayou" },
            views: [[false, "list"]],
        });

        assert.containsOnce(target, ".o_list_view", "should display the list view");

        // Sort the list
        await click(document.querySelector(".o_column_sortable"));

        // Group It
        await toggleGroupByMenu(target);
        await toggleAddCustomGroup(target);
        await applyGroup(target);

        // add this action to dashboard
        await toggleFavoriteMenu(target);

        await testUtils.dom.triggerEvent($(".o_add_to_board button.dropdown-toggle"), "mouseenter");
        await testUtils.fields.editInput($(".o_add_to_board input"), "a name");
        await testUtils.dom.click($(".o_add_to_board .dropdown-menu button"));
    });

    QUnit.test("save two searches to dashboard", async function (assert) {
        // the second search saved should not be influenced by the first
        assert.expect(2);

        patchWithCleanup(browser, { setTimeout: (fn) => fn() });
        serverData.views = {
            "partner,false,list": '<list><field name="foo"/></list>',
            "partner,false,search": "<search></search>",
        };

        const mockRPC = (route, args) => {
            if (route === "/board/add_to_dashboard") {
                if (filter_count === 0) {
                    assert.deepEqual(
                        args.domain,
                        [["display_name", "ilike", "a"]],
                        "the correct domain should be sent"
                    );
                }
                if (filter_count === 1) {
                    assert.deepEqual(
                        args.domain,
                        [["display_name", "ilike", "b"]],
                        "the correct domain should be sent"
                    );
                }

                filter_count += 1;
                return Promise.resolve(true);
            }
        };

        const webClient = await createWebClient({ serverData, mockRPC });

        await doAction(webClient, {
            id: 1,
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
        });

        var filter_count = 0;
        // Add a first filter
        await toggleFilterMenu(target);
        await toggleAddCustomFilter(target);
        await editConditionValue(target, 0, "a");
        await applyFilter(target);

        // Add it to dashboard
        await toggleFavoriteMenu(target);
        await testUtils.dom.triggerEvent($(".o_add_to_board button.dropdown-toggle"), "mouseenter");
        await testUtils.dom.click($(".o_add_to_board .dropdown-menu button"));

        // Remove it
        await testUtils.dom.click(target.querySelector(".o_facet_remove"));

        // Add the second filter
        await toggleFilterMenu(target);
        await toggleAddCustomFilter(target);
        await editConditionValue(target, 0, "b");
        await applyFilter(target);
        // Add it to dashboard
        await toggleFavoriteMenu(target);
        await testUtils.dom.triggerEvent(
            target.querySelector(".o_add_to_board button.dropdown-toggle"),
            "mouseenter"
        );
        await testUtils.dom.click(target.querySelector(".o_add_to_board .dropdown-menu button"));
    });

    QUnit.test("save a action domain to dashboard", async function (assert) {
        // View domains are to be added to the dashboard domain
        assert.expect(1);

        patchWithCleanup(browser, { setTimeout: (fn) => fn() });
        var view_domain = ["display_name", "ilike", "a"];
        var filter_domain = ["display_name", "ilike", "b"];

        var expected_domain = ["&", view_domain, filter_domain];

        serverData.views = {
            "partner,false,list": '<list><field name="foo"/></list>',
            "partner,false,search": "<search></search>",
        };

        const mockRPC = (route, args) => {
            if (route === "/board/add_to_dashboard") {
                assert.deepEqual(args.domain, expected_domain, "the correct domain should be sent");
                return Promise.resolve(true);
            }
        };

        const webClient = await createWebClient({ serverData, mockRPC });

        await doAction(webClient, {
            id: 1,
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
            domain: [view_domain],
        });

        // Add a filter
        await toggleFilterMenu(target);
        await toggleAddCustomFilter(target);
        await editConditionValue(target, 0, "b");
        await applyFilter(target);
        // Add it to dashboard
        await toggleFavoriteMenu(target);
        await testUtils.dom.triggerEvent(
            target.querySelector(".o_add_to_board button.dropdown-toggle"),
            "mouseenter"
        );
        // add
        await testUtils.dom.click(target.querySelector(".o_add_to_board .dropdown-menu button"));
    });

    QUnit.test(
        "correctly save the time ranges of a reporting view in comparison mode",
        async function (assert) {
            assert.expect(1);

            const unpatchDate = patchDate(2020, 6, 1, 11, 0, 0);

            serverData.models.partner.fields.date = {
                string: "Date",
                type: "date",
                sortable: true,
            };

            serverData.views = {
                "partner,false,pivot": '<pivot><field name="foo"/></pivot>',
                "partner,false,search": '<search><filter name="Date" date="date"/></search>',
            };

            const mockRPC = (route, args) => {
                if (route === "/board/add_to_dashboard") {
                    assert.deepEqual(args.context_to_save.comparison, {
                        comparisonId: "previous_period",
                        fieldName: "date",
                        fieldDescription: "Date",
                        rangeDescription: "July 2020",
                        range: ["&", ["date", ">=", "2020-07-01"], ["date", "<=", "2020-07-31"]],
                        comparisonRange: [
                            "&",
                            ["date", ">=", "2020-06-01"],
                            ["date", "<=", "2020-06-30"],
                        ],
                        comparisonRangeDescription: "June 2020",
                    });
                    return Promise.resolve(true);
                }
            };

            registry.category("services").add("user", makeFakeUserService());

            patchWithCleanup(browser, { setTimeout: (fn) => fn() }); // makes mouseEnter work

            const webClient = await createWebClient({ serverData, mockRPC });

            await doAction(webClient, {
                id: 1,
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [[false, "pivot"]],
            });

            // filter on July 2020
            await toggleFilterMenu(target);
            await toggleMenuItem(target, "Date");
            await toggleMenuItemOption(target, "Date", "July");

            // compare July 2020 to June 2020
            await toggleComparisonMenu(target);
            await toggleMenuItem(target, 0);

            // add the view to the dashboard
            await toggleFavoriteMenu(target);

            await mouseEnter(target.querySelector(".o_add_to_board .dropdown-toggle"));
            const input = target.querySelector(".o_add_to_board .dropdown-menu input");
            await testUtils.fields.editInput(input, "Pipeline");
            await testUtils.dom.click($(".o_add_to_board div button"));

            unpatchDate();
        }
    );

    QUnit.test("Add a view to dashboard (keynav)", async function (assert) {
        serverData.views = {
            "partner,false,pivot": '<pivot><field name="foo"/></pivot>',
            "partner,false,search": "<search/>",
        };

        registry.category("services").add("user", makeFakeUserService());

        patchWithCleanup(browser, { setTimeout: (fn) => fn() }); // makes mouseEnter work

        const mockRPC = (route) => {
            if (route === "/board/add_to_dashboard") {
                assert.step("add to board");
                return Promise.resolve(true);
            }
        };

        const webClient = await createWebClient({ serverData, mockRPC });

        await doAction(webClient, {
            id: 1,
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "pivot"]],
        });

        await toggleFavoriteMenu(target);
        await mouseEnter(target.querySelector(".o_add_to_board .dropdown-toggle"));
        const input = target.querySelector(".o_add_to_board .dropdown-menu input");
        await testUtils.fields.editInput(input, "Pipeline");
        await triggerEvent(input, null, "keydown", { key: "Enter" });

        assert.verifySteps(["add to board"]);
    });

    QUnit.test("Add a view with dynamic domain", async function (assert) {
        assert.expect(1);

        serverData.views = {
            "partner,false,pivot": '<pivot><field name="foo"/></pivot>',
            "partner,false,search": `
                <search>
                    <filter name="filter" domain="[('user_id','=',uid)]"/>
                </search>`,
        };

        registry.category("services").add("user", makeFakeUserService());

        patchWithCleanup(browser, { setTimeout: (fn) => fn() }); // makes mouseEnter work

        const mockRPC = (route, args) => {
            if (route === "/board/add_to_dashboard") {
                assert.deepEqual(args.domain, ["&", ["int_field", "<=", 3], ["user_id", "=", 7]]);
                return Promise.resolve(true);
            }
        };

        const webClient = await createWebClient({ serverData, mockRPC });

        await doAction(webClient, {
            id: 1,
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "pivot"]],
            domain: [["int_field", "<=", 3]],
            context: { search_default_filter: 1 },
        });

        await toggleFavoriteMenu(target);
        await mouseEnter(target.querySelector(".o_add_to_board .dropdown-toggle"));
        const input = target.querySelector(".o_add_to_board .dropdown-menu input");
        await testUtils.fields.editInput(input, "Pipeline");
        await triggerEvent(input, null, "keydown", { key: "Enter" });
    });
});
