// @ts-check

import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import {
    Component,
    onWillStart,
    reactive,
    useChildSubEnv,
    useState,
    useSubEnv,
    xml,
} from "@odoo/owl";
import {
    defineModels,
    fields,
    makeMockEnv,
    models,
    mountWithCleanup,
    mountWithSearch,
} from "@web/../tests/web_test_helpers";
import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { SearchModel } from "@web/search/search_model";
import { getDefaultConfig } from "@web/views/view";
import { ViewLayout } from "@web/views/view_components/view_layout";

class Foo extends models.Model {
    aaa = fields.Selection({
        selection: [
            ["a", "A"],
            ["b", "B"],
        ],
    });

    _records = [
        {
            aaa: "a",
        },
        {
            aaa: "b",
        },
    ];

    _views = {
        search: `
            <search>
                <searchpanel>
                    <field name="aaa"/>
                </searchpanel>
            </search>
        `,
    };
}
defineModels([Foo]);

test(`Simple rendering`, async () => {
    class ToyComponent extends Component {
        static props = ["*"];
        static template = xml`
            <Layout className="'o_view_sample_data'" display="this.props.display">
                <div class="toy_content"/>
            </Layout>
        `;
        static components = { Layout };
    }

    await mountWithCleanup(ToyComponent, {
        env: await makeMockEnv({ config: {} }),
    });
    expect(`.o_view_sample_data`).toHaveCount(1);
    expect(`.o_control_panel`).toHaveCount(0);
    expect(`.o_component_with_search_panel`).toHaveCount(0);
    expect(`.o_search_panel`).toHaveCount(0);
    expect(`.o_content > .toy_content`).toHaveCount(1);
});

test(`Simple rendering: with search`, async () => {
    class ToyComponent extends Component {
        static props = ["*"];
        static template = xml`
            <Layout display="this.props.display">
                <t t-set-slot="layout-actions">
                    <div class="toy_search_bar"/>
                </t>
                <div class="toy_content"/>
            </Layout>
        `;
        static components = { Layout };
    }

    await mountWithSearch(ToyComponent, {
        resModel: "foo",
        searchViewId: false,
    });
    expect(`.o_control_panel .o_control_panel_actions .toy_search_bar`).toHaveCount(1);
    expect(`.o_component_with_search_panel .o_search_panel`).toHaveCount(1);
    expect(`.o_cp_searchview`).toHaveCount(0);
    expect(`.o_content > .toy_content`).toHaveCount(1);
});

test(`Rendering with default ControlPanel and SearchPanel`, async () => {
    class ToyComponent extends Component {
        static props = ["*"];
        static template = xml`
            <Layout className="'o_view_sample_data'" display="{ controlPanel: {}, searchPanel: true }">
                <div class="toy_content"/>
            </Layout>
        `;
        static components = { Layout };

        setup() {
            this.searchModel = new SearchModel(
                /** @type {import("@web/env").OdooEnv} */ (this.env),
                {
                    orm: useService("orm"),
                    view: useService("view"),
                },
            );
            useSubEnv({ searchModel: this.searchModel });
            onWillStart(async () => {
                await this.searchModel.load({ resModel: "foo", searchViewId: false });
            });
        }
    }

    await mountWithCleanup(ToyComponent, {
        env: await makeMockEnv({
            config: {
                breadcrumbs: getDefaultConfig().breadcrumbs,
            },
        }),
    });
    expect(`.o_search_panel`).toHaveCount(1);
    expect(`.o_control_panel`).toHaveCount(1);
    expect(`.o_breadcrumb`).toHaveCount(1);
    expect(`.o_component_with_search_panel`).toHaveCount(1);
    expect(`.o_content > .toy_content`).toHaveCount(1);
});

test(`Nested layouts`, async () => {
    class ToyC extends Component {
        static props = ["*"];
        static template = xml`
            <Layout className="'toy_c'" display="this.display">
                <div class="toy_c_content"/>
            </Layout>
        `;
        static components = { Layout };

        get display() {
            return {
                controlPanel: false,
                searchPanel: true,
            };
        }
    }

    class SearchPanel extends Component {
        static props = ["*"];
        static template = xml`<div class="o_toy_search_panel"/>`;
    }

    class ToyB extends Component {
        static props = ["*"];
        static template = xml`
            <Layout className="'toy_b'" display="this.props.display">
                <t t-set-slot="layout-actions">
                    <div class="toy_b_breadcrumbs"/>
                </t>
                <ToyC/>
            </Layout>
        `;
        static components = { Layout, ToyC };
        setup() {
            useChildSubEnv({
                config: {
                    ...getDefaultConfig(),
                    SearchPanel,
                },
            });
        }
    }

    class ToyA extends Component {
        static props = ["*"];
        static template = xml`
            <Layout className="'toy_a'" display="this.props.display">
                <t t-set-slot="layout-actions">
                    <div class="toy_a_search"/>
                </t>
                <ToyB display="this.props.display"/>
            </Layout>
        `;
        static components = { Layout, ToyB };
    }

    await mountWithSearch(ToyA, {
        resModel: "foo",
        searchViewId: false,
    });
    expect(`.o_content.toy_a .o_content.toy_b .o_content.toy_c`).toHaveCount(1);
    expect(".o_control_panel").toHaveCount(2);
    expect(".o_content.o_component_with_search_panel").toHaveCount(3);
    expect(`.o_search_panel`).toHaveCount(1);
    expect(".o_toy_search_panel").toHaveCount(2);
    expect(`.toy_a_search`).toHaveCount(1);
    expect(`.toy_b_breadcrumbs`).toHaveCount(1);
    expect(`.toy_c_content`).toHaveCount(1);
});

test(`Custom control panel`, async () => {
    class ToyComponent extends Component {
        static props = ["*"];
        static template = xml`
            <Layout display="this.props.display">
                <div class="o_toy_content"/>
            </Layout>
        `;
        static components = { Layout };
    }

    class ControlPanel extends Component {
        static props = ["*"];
        static template = xml`<div class="o_toy_search_panel"/>`;
    }

    await mountWithSearch(
        ToyComponent,
        {
            resModel: "foo",
            searchViewId: false,
        },
        { ControlPanel },
    );
    expect(`.o_toy_content`).toHaveCount(1);
    expect(`.o_toy_search_panel`).toHaveCount(1);
    expect(`.o_control_panel`).toHaveCount(0);
});

test(`Custom search panel`, async () => {
    class ToyComponent extends Component {
        static props = ["*"];
        static template = xml`
            <Layout display="this.props.display">
                <div class="o_toy_content"/>
            </Layout>
        `;
        static components = { Layout };
    }

    class SearchPanel extends Component {
        static props = ["*"];
        static template = xml`<div class="o_toy_search_panel"/>`;
    }

    await mountWithSearch(
        ToyComponent,
        {
            resModel: "foo",
            searchViewId: false,
        },
        { SearchPanel },
    );
    expect(`.o_toy_content`).toHaveCount(1);
    expect(`.o_toy_search_panel`).toHaveCount(1);
    expect(`.o_search_panel`).toHaveCount(0);
});

test(`Simple rendering: with dynamically displayed search`, async () => {
    const state = reactive({ displayLayoutActions: true });

    class ToyComponent extends Component {
        static props = ["*"];
        static template = xml`
            <Layout display="this.display">
                <t t-set-slot="layout-actions">
                    <div class="toy_search_bar"/>
                </t>
                <div class="toy_content"/>
            </Layout>
        `;
        static components = { Layout };

        setup() {
            this.state = useState(state);
        }

        get display() {
            return {
                ...this.props.display,
                controlPanel: {
                    ...this.props.display.controlPanel,
                    layoutActions: this.state.displayLayoutActions,
                },
            };
        }
    }

    await mountWithSearch(ToyComponent, {
        resModel: "foo",
        searchViewId: false,
    });
    expect(`.o_control_panel .o_control_panel_actions .toy_search_bar`).toHaveCount(1);
    expect(`.o_component_with_search_panel .o_search_panel`).toHaveCount(1);
    expect(`.o_cp_searchview`).toHaveCount(0);
    expect(`.o_content > .toy_content`).toHaveCount(1);

    state.displayLayoutActions = false;
    await animationFrame();
    expect(`.o_control_panel .o_control_panel_actions .toy_search_bar`).toHaveCount(0);
    expect(`.o_component_with_search_panel .o_search_panel`).toHaveCount(1);
    expect(`.o_cp_searchview`).toHaveCount(0);
    expect(`.o_content > .toy_content`).toHaveCount(1);
});

test(`ViewLayout: layout-actions-start renders before the search bar, layout-actions after it`, async () => {
    class ToyComponent extends Component {
        static props = ["*"];
        static template = xml`
            <ViewLayout display="this.props.display">
                <t t-set-slot="layout-actions-start">
                    <div class="toy_before"/>
                </t>
                <t t-set-slot="layout-actions">
                    <div class="toy_after"/>
                </t>
                <div class="toy_content"/>
            </ViewLayout>
        `;
        static components = { ViewLayout };
    }

    await mountWithSearch(ToyComponent, {
        resModel: "foo",
        searchViewId: false,
    });
    expect(`.o_control_panel_actions .toy_before + .o_cp_searchview`).toHaveCount(1);
    expect(`.o_control_panel_actions .o_cp_searchview + .toy_after`).toHaveCount(1);
    expect(`.o_content > .toy_content`).toHaveCount(1);
});

test(`ViewLayout: a no-content slot replaces the ActionHelper`, async () => {
    class ToyComponent extends Component {
        static props = ["*"];
        static template = xml`
            <ViewLayout display="this.props.display" displayNoContent="true" noContentHelp="'standard help'">
                <t t-set-slot="no-content">
                    <div class="toy_no_content">nothing here</div>
                </t>
                <div class="toy_content"/>
            </ViewLayout>
        `;
        static components = { ViewLayout };
    }

    await mountWithSearch(ToyComponent, {
        resModel: "foo",
        searchViewId: false,
    });
    expect(`.o_content .toy_no_content`).toHaveCount(1);
    expect(`.o_content .o_view_nocontent`).toHaveCount(0);
    expect(`.o_content > .toy_content`).toHaveCount(1);
});
