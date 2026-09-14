// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import {
    Component,
    onWillStart,
    onWillUpdateProps,
    useState,
    useSubEnv,
    xml,
} from "@odoo/owl";
import {
    defineModels,
    fields,
    getMenuItemTexts,
    models,
    mountWithCleanup,
    mountWithSearch,
    onRpc,
    toggleMenuItem,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";
import { SearchModelEvent } from "@web/core/events";
import { SearchBarMenu } from "@web/search/search_bar_menu/search_bar_menu";
import { WithSearch } from "@web/search/with_search/with_search";

class Animal extends models.Model {
    name = fields.Char();
    birthday = fields.Date({ groupable: false });
    type = fields.Selection({
        groupable: false,
        selection: [
            ["omnivorous", "Omnivorous"],
            ["herbivorous", "Herbivorous"],
            ["carnivorous", "Carnivorous"],
        ],
    });

    _views = {
        ["search,1"]: `
            <search>
                <filter name="filter" string="True domain" domain="[(1, '=', 1)]"/>
                <filter name="group_by" context="{ 'group_by': 'name' }"/>
            </search>
        `,
    };
}

defineModels([Animal]);

test("simple rendering", async () => {
    class TestComponent extends Component {
        static props = ["*"];
        static template = xml`<div class="o_test_component">Test component content</div>`;
    }

    await mountWithSearch(TestComponent, {
        resModel: "animal",
    });
    expect(".o_test_component").toHaveCount(1);
    expect(".o_test_component").toHaveText("Test component content");
});

test("search model in sub env", async () => {
    class TestComponent extends Component {
        static props = ["*"];
        static template = xml`<div class="o_test_component">Test component content</div>`;
    }

    const component = await mountWithSearch(TestComponent, {
        resModel: "animal",
    });
    expect(component.env.searchModel).not.toBeEmpty();
});

test("search query props are passed as props to concrete component", async () => {
    class TestComponent extends Component {
        static props = ["*"];
        static template = xml`<div class="o_test_component">Test component content</div>`;

        setup() {
            expect.step("setup");
            const { context, domain, groupBy, orderBy } = this.props;
            expect(context).toEqual({
                allowed_company_ids: [1],
                lang: "en",
                tz: "taht",
                uid: 7,
                key: "val",
            });
            expect(domain).toEqual([[0, "=", 1]]);
            expect(groupBy).toEqual(["birthday"]);
            expect(orderBy).toEqual([{ name: "bar", asc: true }]);
        }
    }

    await mountWithSearch(TestComponent, {
        resModel: "animal",
        domain: [[0, "=", 1]],
        groupBy: ["birthday"],
        context: { key: "val" },
        orderBy: [{ name: "bar", asc: true }],
    });
    expect.verifySteps(["setup"]);
});

test("do not load search view description by default", async () => {
    class TestComponent extends Component {
        static props = ["*"];
        static template = xml`<div class="o_test_component">Test component content</div>`;
    }

    onRpc("get_views", ({ method }) => {
        expect.step(method);
        throw new Error("No get_views should be done");
    });
    await mountWithSearch(TestComponent, {
        resModel: "animal",
    });
    expect.verifySteps([]);
});

test("load search view description if not provided and loadSearchView=true", async () => {
    class TestComponent extends Component {
        static props = ["*"];
        static template = xml`<div class="o_test_component">Test component content</div>`;
    }

    onRpc("get_views", ({ method, kwargs }) => {
        expect.step(method);
        delete kwargs.options.mobile;
        expect(kwargs).toMatchObject({
            options: {
                action_id: false,
                load_filters: false,
                toolbar: false,
                embedded_action_id: false,
                embedded_parent_res_id: false,
            },
            views: [[false, "search"]],
        });
    });
    await mountWithSearch(TestComponent, {
        resModel: "animal",
        searchViewId: false,
    });
    expect.verifySteps(["get_views"]);
});

test("do not load the search view description if provided even if loadSearchView=true", async () => {
    class TestComponent extends Component {
        static props = ["*"];
        static template = xml`<div class="o_test_component">Test component content</div>`;
    }

    onRpc("get_views", ({ method }) => {
        expect.step(method);
        throw new Error("No get_views should be done");
    });
    await mountWithSearch(TestComponent, {
        resModel: "animal",
        searchViewArch: "<search/>",
        searchViewFields: {},
        searchViewId: false,
    });
    expect.verifySteps([]);
});

test("load view description if it is not complete and loadSearchView=true", async () => {
    class TestComponent extends Component {
        static props = ["*"];
        static template = xml`<div class="o_test_component">Test component content</div>`;
    }

    onRpc("get_views", ({ method, kwargs }) => {
        expect.step(method);
        delete kwargs.options.mobile;
        expect(kwargs.options).toEqual({
            action_id: false,
            load_filters: true,
            toolbar: false,
            arch: false,
            embedded_action_id: false,
            embedded_parent_res_id: false,
        });
    });
    await mountWithSearch(TestComponent, {
        resModel: "animal",
        searchViewArch: "<search/>",
        searchViewFields: {},
        searchViewId: true,
        loadIrFilters: true,
    });
    expect.verifySteps(["get_views"]);
});

test("load view description with given id if it is not provided and loadSearchView=true", async () => {
    class TestComponent extends Component {
        static props = ["*"];
        static components = { SearchBarMenu };
        static template = xml`<div class="o_test_component"><SearchBarMenu/></div>`;
    }

    onRpc("get_views", ({ method, kwargs }) => {
        expect.step(method);
        expect(kwargs.views).toEqual([[1, "search"]]);
    });
    await mountWithSearch(TestComponent, {
        resModel: "animal",
        searchViewId: 1,
    });
    expect.verifySteps(["get_views"]);

    await toggleSearchBarMenu();
    expect(getMenuItemTexts()).toEqual([
        "True domain",
        "Custom Filter...",
        "Name",
        "Custom Group\nCreated on\nDisplay name\nLast Modified on\nName",
        "Save current search",
    ]);
});

test("toggle a filter render the underlying component with an updated domain", async () => {
    class TestComponent extends Component {
        static props = ["*"];
        static components = { SearchBarMenu };
        static template = xml`<div class="o_test_component"><SearchBarMenu/></div>`;

        setup() {
            onWillStart(() => {
                expect.step("willStart");
                expect(this.props.domain).toEqual([]);
            });
            onWillUpdateProps((nextProps) => {
                expect.step("willUpdateProps");
                expect(nextProps.domain).toEqual([[1, "=", 1]]);
            });
        }
    }

    await mountWithSearch(TestComponent, {
        resModel: "animal",
        searchViewId: 1,
    });
    expect.verifySteps(["willStart"]);

    await toggleSearchBarMenu();
    await toggleMenuItem("True domain");
    expect.verifySteps(["willUpdateProps"]);
});

test("react to prop 'domain' changes", async () => {
    class TestComponent extends Component {
        static props = ["*"];
        static template = xml`<div class="o_test_component">Test component content</div>`;

        setup() {
            onWillStart(() => {
                expect.step("willStart");
                expect(this.props.domain).toEqual([["type", "=", "carnivorous"]]);
            });
            onWillUpdateProps((nextProps) => {
                expect.step("willUpdateProps");
                expect(nextProps.domain).toEqual([["type", "=", "herbivorous"]]);
            });
        }
    }

    class Parent extends Component {
        static props = ["*"];
        static template = xml`
            <WithSearch t-props="searchState" t-slot-scope="search">
                <TestComponent domain="search.domain"/>
            </WithSearch>
        `;
        static components = { WithSearch, TestComponent };
        setup() {
            useSubEnv({ config: {} });
            this.searchState = useState({
                resModel: "animal",
                domain: [["type", "=", "carnivorous"]],
            });
        }
    }

    const parent = await mountWithCleanup(Parent);
    expect.verifySteps(["willStart"]);

    parent.searchState.domain = [["type", "=", "herbivorous"]];
    await animationFrame();
    expect.verifySteps(["willUpdateProps"]);
});

test("reload with partial props preserves the unspecified search keys", async () => {
    /** @type {import("@web/search/search_model").SearchModel} */
    let searchModel;
    class TestComponent extends Component {
        static props = ["*"];
        static template = xml`<div class="o_test_component">Test component content</div>`;
        setup() {
            searchModel = this.env.searchModel;
        }
    }

    class Parent extends Component {
        static props = ["*"];
        static template = xml`
            <WithSearch t-props="searchProps" t-slot-scope="search">
                <TestComponent/>
            </WithSearch>
        `;
        static components = { WithSearch, TestComponent };
        setup() {
            useSubEnv({ config: {} });
            this.state = useState({
                domain: [["type", "=", "carnivorous"]],
                withOptionalKeys: true,
            });
        }
        get searchProps() {
            const props = { resModel: "animal", domain: this.state.domain };
            if (this.state.withOptionalKeys) {
                Object.assign(props, {
                    context: { key: "val" },
                    groupBy: ["name"],
                    orderBy: [{ name: "name", asc: true }],
                });
            }
            return props;
        }
    }

    const parent = await mountWithCleanup(Parent);
    expect(searchModel.globalContext.key).toBe("val");

    parent.state.withOptionalKeys = false;
    parent.state.domain = [["type", "=", "herbivorous"]];
    await animationFrame();

    expect(searchModel.globalDomain).toEqual([["type", "=", "herbivorous"]]);
    expect(searchModel.globalContext.key).toBe("val");
    expect(searchModel.globalGroupBy).toEqual(["name"]);
    expect(searchModel.globalOrderBy).toEqual([{ name: "name", asc: true }]);
});

test("search defaults are removed from context at reload", async function () {
    const context = {
        search_default_x: true,
        searchpanel_default_y: true,
    };

    class TestComponent extends Component {
        static template = xml`<div class="o_test_component">Test component content</div>`;
        static props = { context: Object };
        setup() {
            onWillStart(() => {
                expect.step("willStart");
                expect(this.props.context).toEqual({
                    lang: "en",
                    tz: "taht",
                    uid: 7,
                    allowed_company_ids: [1],
                });
            });
            onWillUpdateProps((nextProps) => {
                expect.step("willUpdateProps");
                expect(nextProps.context).toEqual({
                    lang: "en",
                    tz: "taht",
                    uid: 7,
                    allowed_company_ids: [1],
                });
            });
        }
    }

    class Parent extends Component {
        static props = ["*"];
        static template = xml`
            <WithSearch t-props="searchState" t-slot-scope="search">
                <TestComponent
                    context="search.context"
                />
            </WithSearch>
        `;
        static components = { WithSearch, TestComponent };
        setup() {
            useSubEnv({ config: {} });
            this.searchState = useState({
                resModel: "animal",
                domain: [["type", "=", "carnivorous"]],
                context,
            });
        }
    }

    const parent = await mountWithCleanup(Parent);
    expect.verifySteps(["willStart"]);

    expect(parent.searchState.context).toEqual(context);

    parent.searchState.domain = [["type", "=", "herbivorous"]];

    await animationFrame();
    expect.verifySteps(["willUpdateProps"]);
    expect(parent.searchState.context).toEqual(context);
});

describe("a query mutation racing a props-driven reload", () => {
    class RacedRecord extends models.Model {
        _name = "raced.record";
        name = fields.Char();
        type = fields.Selection({
            selection: [
                ["omnivorous", "Omnivorous"],
                ["carnivorous", "Carnivorous"],
            ],
        });
        owner_id = fields.Many2one({ string: "Owner", relation: "raced.owner" });
        _records = [{ id: 1, type: "omnivorous", owner_id: 1 }];
    }
    class RacedOwner extends models.Model {
        _name = "raced.owner";
        name = fields.Char();
        _records = [{ id: 1, name: "owner" }];
    }
    defineModels([RacedRecord, RacedOwner]);

    const ARCH = `
        <search>
            <filter name="f1" string="F1" domain="[('type', '=', 'omnivorous')]"/>
            <filter name="f2" string="F2" domain="[('type', '=', 'carnivorous')]"/>
            <searchpanel><field name="friend_id" enable_counters="1"/></searchpanel>
        </search>`;

    async function mountReactive() {
        let searchModel = null;
        const renderedDomains = [];
        class Child extends Component {
            static props = ["*"];
            static template = xml`<div class="o_child" t-esc="tag"/>`;
            setup() {
                searchModel = this.env.searchModel;
            }
            get tag() {
                renderedDomains.push(JSON.stringify(this.props.domain));
                return renderedDomains.length;
            }
        }
        class Parent extends Component {
            static props = ["*"];
            static components = { WithSearch, Child };
            static template = xml`
                <WithSearch t-props="searchProps" t-slot-scope="search">
                    <Child domain="search.domain"/>
                </WithSearch>`;
            setup() {
                useSubEnv({ config: {} });
                this.state = useState({ domain: [] });
            }
            get searchProps() {
                return {
                    resModel: "raced.record",
                    searchViewId: false,
                    searchViewArch: ARCH,
                    domain: this.state.domain,
                };
            }
        }
        const parent = await mountWithCleanup(Parent);
        return { parent, searchModel, renderedDomains };
    }

    function gateSectionFetches() {
        const gate = new Deferred();
        let calls = 0;
        onRpc("search_panel_select_range", async () => {
            calls++;
            if (calls > 1) {
                await gate;
            }
            return { parent_field: false, values: [] };
        });
        return gate;
    }

    test("the mutation is not swallowed", async () => {
        const gate = gateSectionFetches();
        const { parent, searchModel, renderedDomains } = await mountReactive();
        let updates = 0;
        searchModel.addEventListener(SearchModelEvent.UPDATE, () => updates++);

        parent.state.domain = [["id", "=", 1]];
        await animationFrame();
        expect(searchModel.blockNotification).toBe(true);

        const filterId = Object.values(searchModel.searchItems).find(
            (item) => item.type === "filter",
        ).id;
        searchModel.toggleSearchItem(filterId);

        gate.resolve();
        await animationFrame();
        await animationFrame();

        const expected = ["&", ["id", "=", 1], ["type", "=", "omnivorous"]];
        expect(updates).toBe(1);
        expect(searchModel.domain).toEqual(expected);
        expect(renderedDomains.at(-1)).toBe(JSON.stringify(expected));
    });

    test("several mutations converge to a single update", async () => {
        const gate = gateSectionFetches();
        const { parent, searchModel } = await mountReactive();
        let updates = 0;
        searchModel.addEventListener(SearchModelEvent.UPDATE, () => updates++);

        parent.state.domain = [["id", "=", 1]];
        await animationFrame();

        const [first, second] = Object.values(searchModel.searchItems)
            .filter((item) => item.type === "filter")
            .map((item) => item.id);
        searchModel.toggleSearchItem(first);
        searchModel.toggleSearchItem(second);
        searchModel.toggleSearchItem(second);
        searchModel.toggleSearchItem(first);
        searchModel.toggleSearchItem(first);

        gate.resolve();
        await animationFrame();
        await animationFrame();
        await animationFrame();

        expect(updates).toBe(1);
        expect(searchModel.domain).toEqual([
            "&",
            ["id", "=", 1],
            ["type", "=", "omnivorous"],
        ]);
        expect(searchModel._pendingNotification).toBe(false);
    });

    test("a reload with nothing racing it emits no update at all", async () => {
        onRpc("search_panel_select_range", () => ({
            parent_field: false,
            values: [],
        }));
        const { parent, searchModel } = await mountReactive();
        let updates = 0;
        searchModel.addEventListener(SearchModelEvent.UPDATE, () => updates++);

        parent.state.domain = [["id", "=", 1]];
        await animationFrame();
        await animationFrame();

        expect(updates).toBe(0);
    });
});
