/** @odoo-module **/

import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { getFixture, nextTick } from "@web/../tests/helpers/utils";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { ormService } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { FilterMenu } from "@web/search/filter_menu/filter_menu";
import { GroupByMenu } from "@web/search/group_by_menu/group_by_menu";
import { WithSearch } from "@web/search/with_search/with_search";
import { viewService } from "@web/views/view_service";
import {
    getMenuItemTexts,
    makeWithSearch,
    toggleFilterMenu,
    toggleGroupByMenu,
    toggleMenuItem,
} from "./helpers";

const { Component, hooks, mount, tags } = owl;
const { useState } = hooks;
const { xml } = tags;

const serviceRegistry = registry.category("services");

let serverData;

QUnit.module("Search", (hooks) => {
    hooks.beforeEach(async () => {
        serverData = {
            models: {
                animal: {
                    fields: {
                        birthday: { string: "Birthday", type: "date", store: true },
                        type: {
                            string: "Type",
                            type: "selection",
                            selection: [
                                ["omnivorous", "Omnivorous"],
                                ["herbivorous", "Herbivorous"],
                                ["carnivorous", "Carnivorous"],
                            ],
                            store: true,
                        },
                    },
                },
            },
            views: {
                "animal,false,search": `<search/>`,
                "animal,1,search": `
          <search>
            <filter name="filter" string="True domain" domain="[(1, '=', 1)]"/>
            <filter name="group_by" context="{ 'group_by': 'name' }"/>
          </search>
        `,
            },
        };
        serviceRegistry.add("hotkey", hotkeyService);
        serviceRegistry.add("orm", ormService);
        serviceRegistry.add("view", viewService);
    });

    QUnit.module("WithSearch");

    QUnit.test("simple rendering", async function (assert) {
        assert.expect(2);

        class TestComponent extends Component {}
        TestComponent.template = xml`<div class="o_test_component">Test component content</div>`;

        const component = await makeWithSearch({
            serverData,
            resModel: "animal",
            Component: TestComponent,
        });
        assert.hasClass(component.el, "o_test_component");
        assert.strictEqual(component.el.innerText, "Test component content");
    });

    QUnit.test("search model in sub env", async function (assert) {
        assert.expect(1);

        class TestComponent extends Component {}
        TestComponent.template = xml`<div class="o_test_component">Test component content</div>`;

        const component = await makeWithSearch({
            serverData,
            resModel: "animal",
            Component: TestComponent,
        });
        assert.ok(component.env.searchModel);
    });

    QUnit.test(
        "search query props are passed as props to concrete component",
        async function (assert) {
            assert.expect(4);

            class TestComponent extends Component {
                setup() {
                    const { context, domain, groupBy, orderBy } = this.props;
                    assert.deepEqual(context, {
                        lang: "en",
                        tz: "taht",
                        uid: 7,
                        key: "val",
                    });
                    assert.deepEqual(domain, [[0, "=", 1]]);
                    assert.deepEqual(groupBy, ["birthday"]);
                    assert.deepEqual(orderBy, ["bar"]);
                }
            }
            TestComponent.template = xml`<div class="o_test_component">Test component content</div>`;

            await makeWithSearch({
                serverData,
                resModel: "animal",
                Component: TestComponent,
                domain: [[0, "=", 1]],
                groupBy: ["birthday"],
                context: { key: "val" },
                orderBy: ["bar"],
            });
        }
    );

    QUnit.test("do not load search view description by default", async function (assert) {
        assert.expect(1);

        class TestComponent extends Component {}
        TestComponent.template = xml`<div class="o_test_component">Test component content</div>`;

        await makeWithSearch({
            serverData,
            mockRPC: function (_, args) {
                if (args.method === "load_views") {
                    throw new Error("No load_views should be done");
                }
            },
            resModel: "animal",
            Component: TestComponent,
        });

        assert.ok(true);
    });

    QUnit.test(
        "load search view description if not provided and loadSearchView=true",
        async function (assert) {
            assert.expect(1);

            class TestComponent extends Component {}
            TestComponent.template = xml`<div class="o_test_component">Test component content</div>`;

            await makeWithSearch({
                serverData,
                mockRPC: function (_, args) {
                    if (args.method === "load_views") {
                        assert.deepEqual(args.kwargs, {
                            context: {
                                lang: "en",
                                tz: "taht",
                                uid: 7,
                            },
                            options: {
                                action_id: false,
                                load_filters: false,
                                toolbar: false,
                            },
                            views: [[false, "search"]],
                        });
                    }
                },
                resModel: "animal",
                Component: TestComponent,
                searchViewId: false,
            });
        }
    );

    QUnit.test(
        "do not load the search view description if provided even if loadSearchView=true",
        async function (assert) {
            assert.expect(1);

            class TestComponent extends Component {}
            TestComponent.template = xml`<div class="o_test_component">Test component content</div>`;

            await makeWithSearch({
                serverData,
                mockRPC: function (_, args) {
                    if (args.method === "load_views") {
                        throw new Error("No load_views should be done");
                    }
                },
                resModel: "animal",
                Component: TestComponent,
                searchViewArch: "<search/>",
                searchViewFields: {},
                searchViewId: false,
            });
            assert.ok(true);
        }
    );

    QUnit.test(
        "load view description if it is not complete and loadSearchView=true",
        async function (assert) {
            assert.expect(1);

            class TestComponent extends Component {}
            TestComponent.template = xml`<div class="o_test_component">Test component content</div>`;

            await makeWithSearch({
                serverData,
                mockRPC: function (_, args) {
                    if (args.method === "load_views") {
                        assert.deepEqual(args.kwargs.options, {
                            action_id: false,
                            load_filters: true,
                            toolbar: false,
                        });
                    }
                },
                resModel: "animal",
                Component: TestComponent,
                searchViewArch: "<search/>",
                searchViewFields: {},
                searchViewId: true,
                loadIrFilters: true,
            });
        }
    );

    QUnit.test(
        "load view description with given id if it is not provided and loadSearchView=true",
        async function (assert) {
            assert.expect(3);

            class TestComponent extends Component {}
            TestComponent.components = { FilterMenu, GroupByMenu };
            TestComponent.template = xml`
                <div class="o_test_component">
                    <FilterMenu/>
                    <GroupByMenu/>
                </div>
            `;

            const component = await makeWithSearch({
                serverData,
                mockRPC: function (_, args) {
                    if (args.method === "load_views") {
                        assert.deepEqual(args.kwargs.views, [[1, "search"]]);
                    }
                },
                resModel: "animal",
                Component: TestComponent,
                searchViewId: 1,
            });
            await toggleFilterMenu(component);
            await assert.ok(getMenuItemTexts(component), ["True Domain"]);

            await toggleGroupByMenu(component);
            await assert.ok(getMenuItemTexts(component), ["Name"]);
        }
    );

    QUnit.test(
        "toggle a filter render the underlying component with an updated domain",
        async function (assert) {
            assert.expect(2);

            class TestComponent extends Component {
                async willStart() {
                    assert.deepEqual(this.props.domain, []);
                }
                async willUpdateProps(nextProps) {
                    assert.deepEqual(nextProps.domain, [[1, "=", 1]]);
                }
            }
            TestComponent.components = { FilterMenu };
            TestComponent.template = xml`
                <div class="o_test_component">
                    <FilterMenu/>
                </div>
            `;

            const component = await makeWithSearch({
                serverData,
                resModel: "animal",
                Component: TestComponent,
                searchViewId: 1,
            });
            await toggleFilterMenu(component);
            await toggleMenuItem(component, "True domain");
        }
    );

    QUnit.test("react to prop 'domain' changes", async function (assert) {
        assert.expect(2);

        class TestComponent extends Component {
            willStart() {
                assert.deepEqual(this.props.domain, [["type", "=", "carnivorous"]]);
            }
            willUpdateProps(nextProps) {
                assert.deepEqual(nextProps.domain, [["type", "=", "herbivorous"]]);
            }
        }
        TestComponent.template = xml`<div class="o_test_component">Test component content</div>`;

        const env = await makeTestEnv(serverData);
        const target = getFixture();

        class Parent extends Component {
            setup() {
                this.state = useState({
                    resModel: "animal",
                    Component: TestComponent,
                    domain: [["type", "=", "carnivorous"]],
                });
            }
        }
        Parent.template = xml`<WithSearch t-props="state"/>`;
        Parent.components = { WithSearch };

        const parent = await mount(Parent, { env, target });

        parent.state.domain = [["type", "=", "herbivorous"]];

        await nextTick();

        parent.destroy();
    });
});
