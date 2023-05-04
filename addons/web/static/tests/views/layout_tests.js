/** @odoo-module **/

import { getFixture, mount, nextTick } from "@web/../tests/helpers/utils";
import { makeWithSearch, setupControlPanelServiceRegistry } from "@web/../tests/search/helpers";
import { Layout } from "@web/search/layout";
import { getDefaultConfig } from "@web/views/view";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";

import { Component, xml, useChildSubEnv } from "@odoo/owl";

let target;
let serverData;

QUnit.module("Views", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                foo: {
                    fields: {
                        aaa: {
                            type: "selection",
                            selection: [
                                ["a", "A"],
                                ["b", "B"],
                            ],
                        },
                    },
                    records: [],
                },
            },
            views: {
                "foo,false,search": /* xml */ `
                    <search>
                        <searchpanel>
                            <field name="aaa" />
                        </searchpanel>
                    </search>`,
            },
        };

        setupControlPanelServiceRegistry();

        target = getFixture();
    });

    QUnit.module("Layout");

    QUnit.test("Simple rendering", async (assert) => {
        class ToyComponent extends Component {}
        ToyComponent.template = xml`
            <Layout className="'o_view_sample_data'" display="props.display">
                <div class="toy_content" />
            </Layout>`;
        ToyComponent.components = { Layout };

        const env = await makeTestEnv();
        const toyEnv = Object.assign(Object.create(env), { config: {} });
        await mount(ToyComponent, getFixture(), { env: toyEnv });

        assert.containsOnce(target, ".o_view_sample_data");
        assert.containsNone(target, ".o_control_panel");
        assert.containsNone(target, ".o_component_with_search_panel");
        assert.containsNone(target, ".o_search_panel");
        assert.containsOnce(target, ".o_content > .toy_content");
    });

    QUnit.test("Simple rendering: with search", async (assert) => {
        class ToyComponent extends Component {}
        ToyComponent.template = xml`
            <Layout display="props.display">
                <t t-set-slot="control-panel-top-right">
                    <div class="toy_search_bar" />
                </t>
                <div class="toy_content" />
            </Layout>`;
        ToyComponent.components = { Layout };

        await makeWithSearch({
            serverData,
            Component: ToyComponent,
            resModel: "foo",
            searchViewId: false,
        });

        assert.containsOnce(target, ".o_control_panel .o_cp_top_right .toy_search_bar");
        assert.containsOnce(target, ".o_component_with_search_panel .o_search_panel");
        assert.containsNone(target, ".o_cp_searchview");
        assert.containsOnce(target, ".o_content > .toy_content");
    });

    QUnit.test("Nested layouts", async (assert) => {
        // Component C: bottom (no control panel)
        class ToyC extends Component {
            get display() {
                return {
                    controlPanel: false,
                    searchPanel: true,
                };
            }
        }
        ToyC.template = xml`
            <Layout className="'toy_c'" display="display">
                <div class="toy_c_content" />
            </Layout>`;
        ToyC.components = { Layout };

        // Component B: center (with custom search panel)
        class SearchPanel extends Component {}
        SearchPanel.template = xml`<div class="o_toy_search_panel" />`;

        class ToyB extends Component {
            setup() {
                useChildSubEnv({
                    config: {
                        ...getDefaultConfig(),
                        SearchPanel,
                    },
                });
            }
        }
        ToyB.template = xml`
            <Layout className="'toy_b'" display="props.display">
                <t t-set-slot="control-panel-top-right">
                    <div class="toy_b_breadcrumbs" />
                </t>
                <ToyC/>
            </Layout>`;
        ToyB.components = { Layout, ToyC };

        // Component A: top
        class ToyA extends Component {}
        ToyA.template = xml`
            <Layout className="'toy_a'" display="props.display">
                <t t-set-slot="control-panel-top-right">
                    <div class="toy_a_search" />
                </t>
                <ToyB display="props.display"/>
            </Layout>`;
        ToyA.components = { Layout, ToyB };

        await makeWithSearch({
            serverData,
            Component: ToyA,
            resModel: "foo",
            searchViewId: false,
        });

        assert.containsOnce(target, ".o_content.toy_a .o_content.toy_b .o_content.toy_c"); // Full chain of contents
        assert.containsN(target, ".o_control_panel", 2); // Component C has hidden its control panel
        assert.containsN(target, ".o_content.o_component_with_search_panel", 3);
        assert.containsOnce(target, ".o_search_panel"); // Standard search panel
        assert.containsN(target, ".o_toy_search_panel", 2); // Custom search panels
        assert.containsOnce(target, ".toy_a_search");
        assert.containsOnce(target, ".toy_b_breadcrumbs");
        assert.containsOnce(target, ".toy_c_content");
    });

    QUnit.test("Custom control panel", async (assert) => {
        class ToyComponent extends Component {}
        ToyComponent.template = xml`
            <Layout display="props.display">
                <div class="o_toy_content" />
            </Layout>`;
        ToyComponent.components = { Layout };

        class ControlPanel extends Component {}
        ControlPanel.template = xml`<div class="o_toy_search_panel" />`;

        await makeWithSearch({
            serverData,
            Component: ToyComponent,
            resModel: "foo",
            searchViewId: false,
            config: { ControlPanel },
        });

        assert.containsOnce(target, ".o_toy_content");
        assert.containsOnce(target, ".o_toy_search_panel");
        assert.containsNone(target, ".o_control_panel");
    });

    QUnit.test("Custom search panel", async (assert) => {
        class ToyComponent extends Component {}
        ToyComponent.template = xml`
            <Layout display="props.display">
                <div class="o_toy_content" />
            </Layout>`;
        ToyComponent.components = { Layout };

        class SearchPanel extends Component {}
        SearchPanel.template = xml`<div class="o_toy_search_panel" />`;

        await makeWithSearch({
            serverData,
            Component: ToyComponent,
            resModel: "foo",
            searchViewId: false,
            config: { SearchPanel },
        });

        assert.containsOnce(target, ".o_toy_content");
        assert.containsOnce(target, ".o_toy_search_panel");
        assert.containsNone(target, ".o_search_panel");
    });

    QUnit.test("Custom banner: no bannerRoute in env", async (assert) => {
        class ToyComponent extends Component {}
        ToyComponent.template = xml`
            <Layout display="props.display">
                <div class="o_toy_content" />
            </Layout>`;
        ToyComponent.components = { Layout };

        class Banner extends Component {}
        Banner.template = xml`<div class="o_toy_banner" />`;

        await makeWithSearch({
            serverData,
            Component: ToyComponent,
            resModel: "foo",
            searchViewId: false,
            config: { Banner },
        });

        assert.containsOnce(target, ".o_toy_content");
        assert.containsNone(target, ".o_toy_banner");
    });

    QUnit.test("Custom banner: with bannerRoute in env", async (assert) => {
        class ToyComponent extends Component {}
        ToyComponent.template = xml`
            <Layout display="props.display">
                <div class="o_toy_content" />
            </Layout>`;
        ToyComponent.components = { Layout };

        class Banner extends Component {}
        Banner.template = xml`<div class="o_toy_banner" />`;

        await makeWithSearch({
            serverData,
            Component: ToyComponent,
            resModel: "foo",
            searchViewId: false,
            config: { Banner, bannerRoute: "toy/banner/route" },
        });

        assert.containsOnce(target, ".o_toy_content");
        assert.containsOnce(target, ".o_toy_banner");
        assert.notOk(target.querySelector(".o_toy_banner").closest(".o_content"));
        assert.ok(target.querySelector(".o_toy_content").closest(".o_content"));
    });

    QUnit.test("Simple rendering: with dynamically displayed search", async (assert) => {
        let displayControlPanelTopRight = true;
        class ToyComponent extends Component {
            get display() {
                return {
                    ...this.props.display,
                    controlPanel: {
                        ...this.props.display.controlPanel,
                        "top-right": displayControlPanelTopRight,
                    },
                };
            }
        }
        ToyComponent.template = xml`
            <Layout display="display">
                <t t-set-slot="control-panel-top-right">
                    <div class="toy_search_bar" />
                </t>
                <div class="toy_content" />
            </Layout>`;
        ToyComponent.components = { Layout };

        const comp = await makeWithSearch({
            serverData,
            Component: ToyComponent,
            resModel: "foo",
            searchViewId: false,
        });

        assert.containsOnce(target, ".o_control_panel .o_cp_top_right .toy_search_bar");
        assert.containsOnce(target, ".o_component_with_search_panel .o_search_panel");
        assert.containsNone(target, ".o_cp_searchview");
        assert.containsOnce(target, ".o_content > .toy_content");

        displayControlPanelTopRight = false;
        comp.render();
        await nextTick();

        assert.containsNone(target, ".o_control_panel .o_cp_top_right .toy_search_bar");
        assert.containsOnce(target, ".o_component_with_search_panel .o_search_panel");
        assert.containsNone(target, ".o_cp_searchview");
        assert.containsOnce(target, ".o_content > .toy_content");
    });
});
