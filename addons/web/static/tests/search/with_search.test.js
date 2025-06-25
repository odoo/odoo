import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, onWillStart, onWillUpdateProps, useState, useSubEnv, xml } from "@odoo/owl";
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
        [["search", 1]]: `
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
