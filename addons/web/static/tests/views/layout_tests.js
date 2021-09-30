/** @odoo-module **/

import { getFixture } from "@web/../tests/helpers/utils";
import { makeWithSearch, setupControlPanelServiceRegistry } from "@web/../tests/search/helpers";
import { dialogService } from "@web/core/dialog/dialog_service";
import { registry } from "@web/core/registry";
import { Layout } from "@web/views/layout";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";

const { Component, hooks, mount, tags } = owl;
const { xml } = tags;
const { useSubEnv } = hooks;

const serviceRegistry = registry.category("services");

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
        serviceRegistry.add("dialog", dialogService);
    });

    QUnit.module("Layout");

    QUnit.test("Simple rendering", async (assert) => {
        assert.expect(5);

        class ToyComponent extends Component {}
        ToyComponent.template = xml`
            <Layout viewType="'toy'" useSampleModel="true">
                <div class="toy_content" />
            </Layout>`;
        ToyComponent.components = { Layout };

        const env = await makeTestEnv({ config: {} });
        const comp = await mount(ToyComponent, { target: getFixture(), env });

        assert.hasClass(comp.el, "o_toy_view o_view_sample_data");
        assert.containsNone(comp, ".o_control_panel");
        assert.containsNone(comp, ".o_component_with_search_panel");
        assert.containsNone(comp, ".o_search_panel");
        assert.containsOnce(comp, ".o_content > .toy_content");
    });

    QUnit.test("Simple rendering: with search", async (assert) => {
        assert.expect(6);

        class ToyComponent extends Component {}
        ToyComponent.template = xml`
            <Layout viewType="'toy'">
                <t t-set-slot="control-panel-top-right">
                    <div class="toy_search_bar" />
                </t>
                <div class="toy_content" />
            </Layout>`;
        ToyComponent.components = { Layout };

        const root = await makeWithSearch({
            serverData,
            Component: ToyComponent,
            resModel: "foo",
            searchViewId: false,
        });

        assert.hasClass(root.el, "o_toy_view");
        assert.doesNotHaveClass(root.el, "o_view_sample_data");
        assert.containsOnce(root, ".o_control_panel .o_cp_top_right .toy_search_bar");
        assert.containsOnce(root, ".o_component_with_search_panel .o_search_panel");
        assert.containsNone(root, ".o_cp_searchview");
        assert.containsOnce(root, ".o_content > .toy_content");
    });

    QUnit.test("Nested layouts", async (assert) => {
        assert.expect(10);

        // Component C: bottom (no control panel)

        class ToyC extends Component {
            setup() {
                useSubEnv({
                    searchModel: {
                        display: {
                            controlPanel: false,
                            searchPanel: true,
                        },
                    },
                });
            }
        }
        ToyC.template = xml`
            <Layout viewType="'toy_c'">
                <div class="toy_c_content" />
            </Layout>`;
        ToyC.components = { Layout };

        // Component B: center (with custom search panel)

        class SearchPanel extends Component {}
        SearchPanel.template = xml`<div class="o_toy_search_panel" />`;

        class ToyB extends Component {
            setup() {
                useSubEnv({ config: { SearchPanel } });
            }
        }
        ToyB.template = xml`
            <Layout viewType="'toy_b'">
                <t t-set-slot="control-panel-top-right">
                    <div class="toy_b_breadcrumbs" />
                </t>
                <ToyC />
            </Layout>`;
        ToyB.components = { Layout, ToyC };

        // Component A: top

        class ToyA extends Component {}
        ToyA.template = xml`
            <Layout viewType="'toy_a'">
                <t t-set-slot="control-panel-top-right">
                    <div class="toy_a_search" />
                </t>
                <ToyB />
            </Layout>`;
        ToyA.components = { Layout, ToyB };

        const root = await makeWithSearch({
            serverData,
            Component: ToyA,
            resModel: "foo",
            searchViewId: false,
        });

        assert.hasClass(root.el, "o_toy_a_view");
        assert.doesNotHaveClass(root.el, "o_view_sample_data");
        assert.containsOnce(root, ".o_content .o_toy_b_view .o_content .o_toy_c_view .o_content"); // Full chain of contents
        assert.containsN(root, ".o_control_panel", 2); // Component C has hidden its control panel
        assert.containsN(root, ".o_content.o_component_with_search_panel", 3);
        assert.containsOnce(root, ".o_search_panel"); // Standard search panel
        assert.containsN(root, ".o_toy_search_panel", 2); // Custom search panels
        assert.containsOnce(root, ".toy_a_search");
        assert.containsOnce(root, ".toy_b_breadcrumbs");
        assert.containsOnce(root, ".toy_c_content");
    });

    QUnit.test("Custom control panel", async (assert) => {
        assert.expect(3);

        class ToyComponent extends Component {}
        ToyComponent.template = xml`
            <Layout>
                <div class="o_toy_content" />
            </Layout>`;
        ToyComponent.components = { Layout };

        class ControlPanel extends Component {}
        ControlPanel.template = xml`<div class="o_toy_search_panel" />`;

        const root = await makeWithSearch({
            serverData,
            Component: ToyComponent,
            resModel: "foo",
            searchViewId: false,
            config: { ControlPanel },
        });

        assert.containsOnce(root, ".o_toy_content");
        assert.containsOnce(root, ".o_toy_search_panel");
        assert.containsNone(root, ".o_control_panel");
    });

    QUnit.test("Custom search panel", async (assert) => {
        assert.expect(3);

        class ToyComponent extends Component {}
        ToyComponent.template = xml`
            <Layout>
                <div class="o_toy_content" />
            </Layout>`;
        ToyComponent.components = { Layout };

        class SearchPanel extends Component {}
        SearchPanel.template = xml`<div class="o_toy_search_panel" />`;

        const root = await makeWithSearch({
            serverData,
            Component: ToyComponent,
            resModel: "foo",
            searchViewId: false,
            config: { SearchPanel },
        });

        assert.containsOnce(root, ".o_toy_content");
        assert.containsOnce(root, ".o_toy_search_panel");
        assert.containsNone(root, ".o_search_panel");
    });

    QUnit.test("Custom banner: no bannerRoute in env", async (assert) => {
        assert.expect(2);

        class ToyComponent extends Component {}
        ToyComponent.template = xml`
            <Layout>
                <div class="o_toy_content" />
            </Layout>`;
        ToyComponent.components = { Layout };

        class Banner extends Component {}
        Banner.template = xml`<div class="o_toy_banner" />`;

        const root = await makeWithSearch({
            serverData,
            Component: ToyComponent,
            resModel: "foo",
            searchViewId: false,
            config: { Banner },
        });

        assert.containsOnce(root, ".o_toy_content");
        assert.containsNone(root, ".o_toy_banner");
    });

    QUnit.test("Custom banner: with bannerRoute in env", async (assert) => {
        assert.expect(2);

        class ToyComponent extends Component {}
        ToyComponent.template = xml`
            <Layout>
                <div class="o_toy_content" />
            </Layout>`;
        ToyComponent.components = { Layout };

        class Banner extends Component {}
        Banner.template = xml`<div class="o_toy_banner" />`;

        const root = await makeWithSearch({
            serverData,
            Component: ToyComponent,
            resModel: "foo",
            searchViewId: false,
            config: { Banner, bannerRoute: "toy/banner/route" },
        });

        assert.containsOnce(root, ".o_toy_content");
        assert.containsOnce(root, ".o_toy_banner");
    });
});
