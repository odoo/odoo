/** @odoo-module **/

import { getFixture, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { ormService } from "@web/core/orm_service";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { registry } from "@web/core/registry";
import { View } from "@web/views/view";
import { viewService } from "@web/views/view_service";

const { Component, mount, hooks, tags } = owl;
const { useState } = hooks;
const { xml } = tags;

const serviceRegistry = registry.category("services");
const viewRegistry = registry.category("views");

async function makeView(params) {
    const serverData = params.serverData;
    const mockRPC = params.mockRPC;
    const env = await makeTestEnv({ serverData, mockRPC });

    // we don't want "fields" to be added here !!!
    const props = Object.assign({}, params);
    delete props.serverData;
    delete props.mockRPC;

    const target = getFixture();

    const view = await mount(View, { env, props, target });

    registerCleanup(() => view.destroy());

    const withSearch = Object.values(view.__owl__.children)[0];
    const concreteView = Object.values(withSearch.__owl__.children)[0];

    return concreteView;
}

let serverData;

QUnit.module("Views", (hooks) => {
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
                    filters: [
                        // should be a model!
                        {
                            context: "{}",
                            domain: "[('animal', 'ilike', 'o')]",
                            id: 7,
                            is_default: true,
                            name: "My favorite",
                            sort: "[]",
                            user_id: [2, "Mitchell Admin"],
                        },
                    ],
                },
            },
            views: {
                "animal,false,toy": `<toy>Arch content (id=false)</toy>`,
                "animal,1,toy": `<toy>Arch content (id=1)</toy>`,
                "animal,2,toy": `<toy js_class="toy_imp">Arch content (id=2)</toy>`,
                "animal,false,other": `<other/>`,
                "animal,false,search": `<search/>`,
                "animal,1,search": `
                    <search>
                        <filter name="filter" domain="[(1, '=', 1)]"/>
                        <filter name="group_by" context="{ 'group_by': 'name' }"/>
                    </search>
                `,
            },
        };

        class ToyView extends Component {
            setup() {
                this.class = "o_toy_view";
                this.template = xml`${this.props.arch}`;
            }
        }
        ToyView.template = xml`<div t-att-class="class"><t t-call="{{ template }}"/></div>`;
        ToyView.type = "toy";

        class ToyViewImp extends ToyView {
            setup() {
                super.setup();
                this.class = "o_toy_view_imp";
            }
        }

        viewRegistry.add("toy", ToyView);
        viewRegistry.add("toy_imp", ToyViewImp);

        serviceRegistry.add("orm", ormService);
        serviceRegistry.add("view", viewService);
    });

    QUnit.module("View component");

    ////////////////////////////////////////////////////////////////////////////
    // load_views
    ////////////////////////////////////////////////////////////////////////////

    QUnit.test("simple rendering", async function (assert) {
        assert.expect(10);

        const ToyView = viewRegistry.get("toy");
        patchWithCleanup(ToyView.prototype, {
            setup() {
                this._super();
                const { arch, fields, info } = this.props;
                assert.notOk("actionMenus" in this.props);
                assert.strictEqual(arch, serverData.views["animal,false,toy"]);
                assert.deepEqual(fields, serverData.models.animal.fields);
                assert.strictEqual(info.viewId, false);
            },
        });

        const view = await makeView({
            serverData,
            mockRPC: (_, args) => {
                assert.strictEqual(args.model, "animal");
                assert.strictEqual(args.method, "load_views");
                assert.deepEqual(args.kwargs.views, [[false, "toy"]]);
                assert.deepEqual(args.kwargs.options, {
                    action_id: false,
                    load_filters: false,
                    toolbar: false,
                });
            },
            resModel: "animal",
            type: "toy",
        });
        assert.hasClass(view.el, "o_action o_view_controller o_toy_view");
        assert.strictEqual(view.el.innerHTML, serverData.views["animal,false,toy"]);
    });

    QUnit.test("rendering with given viewId", async function (assert) {
        assert.expect(8);

        const ToyView = viewRegistry.get("toy");
        patchWithCleanup(ToyView.prototype, {
            setup() {
                this._super();
                const { arch, fields, info } = this.props;
                assert.notOk("actionMenus" in this.props);
                assert.strictEqual(arch, serverData.views["animal,1,toy"]);
                assert.deepEqual(fields, serverData.models.animal.fields);
                assert.strictEqual(info.viewId, 1);
            },
        });

        const view = await makeView({
            serverData,
            mockRPC: (_, args) => {
                assert.deepEqual(args.kwargs.views, [[1, "toy"]]);
                assert.deepEqual(args.kwargs.options, {
                    action_id: false,
                    load_filters: false,
                    toolbar: false,
                });
            },
            resModel: "animal",
            type: "toy",
            viewId: 1,
        });
        assert.hasClass(view.el, "o_toy_view");
        assert.strictEqual(view.el.innerHTML, serverData.views["animal,1,toy"]);
    });

    QUnit.test("rendering with given 'views' param", async function (assert) {
        assert.expect(8);

        const ToyView = viewRegistry.get("toy");
        patchWithCleanup(ToyView.prototype, {
            setup() {
                this._super();
                const { arch, fields, info } = this.props;
                assert.notOk("actionMenus" in this.props);
                assert.strictEqual(arch, serverData.views["animal,1,toy"]);
                assert.deepEqual(fields, serverData.models.animal.fields);
                assert.strictEqual(info.viewId, 1);
            },
        });

        const view = await makeView({
            serverData,
            mockRPC: (_, args) => {
                assert.deepEqual(args.kwargs.views, [[1, "toy"]]);
                assert.deepEqual(args.kwargs.options, {
                    action_id: false,
                    load_filters: false,
                    toolbar: false,
                });
            },
            resModel: "animal",
            type: "toy",
            views: [[1, "toy"]],
        });
        assert.hasClass(view.el, "o_toy_view");
        assert.strictEqual(view.el.innerHTML, serverData.views["animal,1,toy"]);
    });

    QUnit.test(
        "rendering with given 'views' param not containing view id",
        async function (assert) {
            assert.expect(8);

            const ToyView = viewRegistry.get("toy");
            patchWithCleanup(ToyView.prototype, {
                setup() {
                    this._super();
                    const { arch, fields, info } = this.props;
                    assert.notOk("actionMenus" in this.props);
                    assert.strictEqual(arch, serverData.views["animal,false,toy"]);
                    assert.deepEqual(fields, serverData.models.animal.fields);
                    assert.strictEqual(info.viewId, false);
                },
            });

            const view = await makeView({
                serverData,
                mockRPC: (_, args) => {
                    assert.deepEqual(args.kwargs.views, [
                        [false, "other"],
                        [false, "toy"],
                    ]);
                    assert.deepEqual(args.kwargs.options, {
                        action_id: false,
                        load_filters: false,
                        toolbar: false,
                    });
                },
                resModel: "animal",
                type: "toy",
                views: [[false, "other"]],
            });
            assert.hasClass(view.el, "o_toy_view");
            assert.strictEqual(view.el.innerHTML, serverData.views["animal,false,toy"]);
        }
    );

    QUnit.test("viewId defined as prop and in 'views' prop", async function (assert) {
        assert.expect(8);

        const ToyView = viewRegistry.get("toy");
        patchWithCleanup(ToyView.prototype, {
            setup() {
                this._super();
                const { arch, fields, info } = this.props;
                assert.notOk("actionMenus" in this.props);
                assert.strictEqual(arch, serverData.views["animal,1,toy"]);
                assert.deepEqual(fields, serverData.models.animal.fields);
                assert.strictEqual(info.viewId, 1);
            },
        });

        const view = await makeView({
            serverData,
            mockRPC: (_, args) => {
                assert.deepEqual(args.kwargs.views, [
                    [1, "toy"],
                    [false, "other"],
                ]);
                assert.deepEqual(args.kwargs.options, {
                    action_id: false,
                    load_filters: false,
                    toolbar: false,
                });
            },
            resModel: "animal",
            type: "toy",
            viewId: 1,
            views: [
                [3, "toy"],
                [false, "other"],
            ],
        });
        assert.hasClass(view.el, "o_toy_view");
        assert.strictEqual(view.el.innerHTML, serverData.views["animal,1,toy"]);
    });

    QUnit.test("rendering with given arch", async function (assert) {
        assert.expect(8);

        const ToyView = viewRegistry.get("toy");
        patchWithCleanup(ToyView.prototype, {
            setup() {
                this._super();
                const { arch, fields, info } = this.props;
                assert.strictEqual(info.actionMenus, undefined);
                assert.strictEqual(arch, `<toy>Specific arch content</toy>`);
                assert.deepEqual(fields, serverData.models.animal.fields);
                assert.strictEqual(info.viewId, false);
            },
        });

        const view = await makeView({
            serverData,
            mockRPC: (_, args) => {
                // the rpc is done for fields
                assert.deepEqual(args.kwargs.views, [[false, "toy"]]);
                assert.deepEqual(args.kwargs.options, {
                    action_id: false,
                    load_filters: false,
                    toolbar: false,
                });
            },
            resModel: "animal",
            type: "toy",
            arch: `<toy>Specific arch content</toy>`,
        });
        assert.hasClass(view.el, "o_toy_view");
        assert.strictEqual(view.el.innerHTML, `<toy>Specific arch content</toy>`);
    });

    QUnit.test("rendering with given arch and fields", async function (assert) {
        assert.expect(6);

        const ToyView = viewRegistry.get("toy");
        patchWithCleanup(ToyView.prototype, {
            setup() {
                this._super();
                const { arch, fields, info } = this.props;
                assert.strictEqual(info.actionMenus, undefined);
                assert.strictEqual(arch, `<toy>Specific arch content</toy>`);
                assert.deepEqual(fields, {});
                assert.notOk("viewId" in this.props);
            },
        });

        const view = await makeView({
            serverData,
            mockRPC: () => {
                throw new Error("no RPC expected");
            },
            resModel: "animal",
            type: "toy",
            arch: `<toy>Specific arch content</toy>`,
            fields: {},
        });
        assert.hasClass(view.el, "o_toy_view");
        assert.strictEqual(view.el.innerHTML, `<toy>Specific arch content</toy>`);
    });

    QUnit.test("rendering with loadActionMenus='true'", async function (assert) {
        assert.expect(8);

        const ToyView = viewRegistry.get("toy");
        patchWithCleanup(ToyView.prototype, {
            setup() {
                this._super();
                const { arch, fields, info } = this.props;
                assert.strictEqual(arch, serverData.views["animal,false,toy"]);
                assert.deepEqual(fields, serverData.models.animal.fields);
                assert.strictEqual(info.viewId, false);
                assert.deepEqual(info.actionMenus, {});
            },
        });

        const view = await makeView({
            serverData,
            mockRPC: (_, args) => {
                // the rpc is done for fields
                assert.deepEqual(args.kwargs.views, [[false, "toy"]]);
                assert.deepEqual(args.kwargs.options, {
                    action_id: false,
                    load_filters: false,
                    toolbar: true,
                });
            },
            resModel: "animal",
            type: "toy",
            loadActionMenus: true,
        });
        assert.hasClass(view.el, "o_toy_view");
        assert.strictEqual(view.el.innerHTML, serverData.views["animal,false,toy"]);
    });

    QUnit.test(
        "rendering with given arch, fields, and loadActionMenus='true'",
        async function (assert) {
            assert.expect(8);

            const ToyView = viewRegistry.get("toy");
            patchWithCleanup(ToyView.prototype, {
                setup() {
                    this._super();
                    const { arch, fields, info } = this.props;
                    assert.strictEqual(arch, `<toy>Specific arch content</toy>`);
                    assert.deepEqual(fields, {});
                    assert.strictEqual(info.viewId, false);
                    assert.deepEqual(info.actionMenus, {});
                },
            });

            const view = await makeView({
                serverData,
                mockRPC: (_, args) => {
                    // the rpc is done for fields
                    assert.deepEqual(args.kwargs.views, [[false, "toy"]]);
                    assert.deepEqual(args.kwargs.options, {
                        action_id: false,
                        load_filters: false,
                        toolbar: true,
                    });
                },
                resModel: "animal",
                type: "toy",
                arch: `<toy>Specific arch content</toy>`,
                fields: {},
                loadActionMenus: true,
            });
            assert.hasClass(view.el, "o_toy_view");
            assert.strictEqual(view.el.innerHTML, `<toy>Specific arch content</toy>`);
        }
    );

    QUnit.test(
        "rendering with given arch, fields, actionMenus, and loadActionMenus='true'",
        async function (assert) {
            assert.expect(6);

            const ToyView = viewRegistry.get("toy");
            patchWithCleanup(ToyView.prototype, {
                setup() {
                    this._super();
                    const { actionMenus, arch, fields } = this.props;
                    assert.strictEqual(arch, `<toy>Specific arch content</toy>`);
                    assert.deepEqual(fields, {});
                    assert.notOk("viewId" in this.props);
                    assert.deepEqual(actionMenus, {});
                },
            });

            const view = await makeView({
                serverData,
                mockRPC: () => {
                    throw new Error("no RPC expected");
                },
                resModel: "animal",
                type: "toy",
                arch: `<toy>Specific arch content</toy>`,
                fields: {},
                actionMenus: {
                    /** ... */
                },
                loadActionMenus: true,
            });
            assert.hasClass(view.el, "o_toy_view");
            assert.strictEqual(view.el.innerHTML, `<toy>Specific arch content</toy>`);
        }
    );

    QUnit.test("rendering with given searchViewId", async function (assert) {
        assert.expect(8);

        const ToyView = viewRegistry.get("toy");
        patchWithCleanup(ToyView.prototype, {
            setup() {
                this._super();
                const { searchViewArch, searchViewFields, searchViewId } = this.props.info;
                assert.strictEqual(searchViewArch, serverData.views["animal,false,search"]);
                assert.deepEqual(searchViewFields, serverData.models.animal.fields);
                assert.strictEqual(searchViewId, false);
                assert.notOk("irFilters" in this.props);
            },
        });

        const view = await makeView({
            serverData,
            mockRPC: (_, args) => {
                // the rpc is done for fields
                assert.deepEqual(args.kwargs.views, [
                    [false, "toy"],
                    [false, "search"],
                ]);
                assert.deepEqual(args.kwargs.options, {
                    action_id: false,
                    load_filters: false,
                    toolbar: false,
                });
            },
            resModel: "animal",
            type: "toy",
            searchViewId: false,
        });
        assert.hasClass(view.el, "o_toy_view");
        assert.strictEqual(view.el.innerText, "Arch content (id=false)");
    });

    QUnit.test(
        "rendering with given arch, fields, searchViewId, searchViewArch, and searchViewFields",
        async function (assert) {
            assert.expect(6);

            const ToyView = viewRegistry.get("toy");
            patchWithCleanup(ToyView.prototype, {
                setup() {
                    this._super();
                    const { searchViewArch, searchViewFields, searchViewId } = this.props.info;
                    assert.strictEqual(searchViewArch, `<search/>`);
                    assert.deepEqual(searchViewFields, {});
                    assert.strictEqual(searchViewId, false);
                    assert.notOk("irFilters" in this.props);
                },
            });

            const view = await makeView({
                serverData,
                mockRPC: () => {
                    throw new Error("no RPC expected");
                },
                resModel: "animal",
                type: "toy",
                arch: `<toy>Specific arch content</toy>`,
                fields: {},
                searchViewId: false,
                searchViewArch: `<search/>`,
                searchViewFields: {},
            });
            assert.hasClass(view.el, "o_toy_view");
            assert.strictEqual(view.el.innerText, "Specific arch content");
        }
    );

    QUnit.test(
        "rendering with given arch, fields, searchViewId, searchViewArch, searchViewFields, and loadIrFilters='true'",
        async function (assert) {
            assert.expect(8);

            const ToyView = viewRegistry.get("toy");
            patchWithCleanup(ToyView.prototype, {
                setup() {
                    this._super();
                    const {
                        irFilters,
                        searchViewArch,
                        searchViewFields,
                        searchViewId,
                    } = this.props.info;
                    assert.strictEqual(searchViewArch, `<search/>`);
                    assert.deepEqual(searchViewFields, {});
                    assert.strictEqual(searchViewId, false);
                    assert.deepEqual(irFilters, serverData.models.animal.filters);
                },
            });

            const view = await makeView({
                serverData,
                mockRPC: (_, args) => {
                    // the rpc is done for fields
                    assert.deepEqual(args.kwargs.views, [
                        [false, "toy"],
                        [false, "search"],
                    ]);
                    assert.deepEqual(args.kwargs.options, {
                        action_id: false,
                        load_filters: true,
                        toolbar: false,
                    });
                },
                resModel: "animal",
                type: "toy",
                arch: `<toy>Specific arch content</toy>`,
                fields: {},
                searchViewId: false,
                searchViewArch: `<search/>`,
                searchViewFields: {},
                loadIrFilters: true,
            });
            assert.hasClass(view.el, "o_toy_view");
            assert.strictEqual(view.el.innerText, "Specific arch content");
        }
    );

    QUnit.test(
        "rendering with given arch, fields, searchViewId, searchViewArch, searchViewFields, irFilters, and loadIrFilters='true'",
        async function (assert) {
            assert.expect(6);
            const irFilters = [
                {
                    context: "{}",
                    domain: "[]",
                    id: 1,
                    is_default: false,
                    name: "My favorite",
                    sort: "[]",
                    user_id: [2, "Mitchell Admin"],
                },
            ];

            const ToyView = viewRegistry.get("toy");
            patchWithCleanup(ToyView.prototype, {
                setup() {
                    this._super();
                    const { irFilters, searchViewArch, searchViewFields } = this.props.info;
                    assert.strictEqual(searchViewArch, `<search/>`);
                    assert.deepEqual(searchViewFields, {});
                    assert.notOk("searchViewId" in this.props);
                    assert.deepEqual(irFilters, irFilters);
                },
            });

            const view = await makeView({
                serverData,
                mockRPC: () => {
                    throw new Error("no RPC expected");
                },
                resModel: "animal",
                type: "toy",
                arch: `<toy>Specific arch content</toy>`,
                fields: {},
                searchViewArch: `<search/>`,
                searchViewFields: {},
                loadIrFilters: true,
                irFilters,
            });
            assert.hasClass(view.el, "o_toy_view");
            assert.strictEqual(view.el.innerText, "Specific arch content");
        }
    );

    ////////////////////////////////////////////////////////////////////////////
    // js_class
    ////////////////////////////////////////////////////////////////////////////

    QUnit.test("rendering with given jsClass", async function (assert) {
        assert.expect(4);
        const view = await makeView({
            serverData,
            mockRPC: (_, args) => {
                assert.deepEqual(args.kwargs.views, [[false, "toy"]]);
                assert.deepEqual(args.kwargs.options, {
                    action_id: false,
                    load_filters: false,
                    toolbar: false,
                });
            },
            resModel: "animal",
            type: "toy_imp",
        });
        assert.hasClass(view.el, "o_toy_view_imp");
        assert.strictEqual(view.el.innerText, "Arch content (id=false)");
    });

    QUnit.test("rendering with loaded arch attribute 'js_class'", async function (assert) {
        assert.expect(4);
        const view = await makeView({
            serverData,
            mockRPC: (_, args) => {
                assert.deepEqual(args.kwargs.views, [[2, "toy"]]);
                assert.deepEqual(args.kwargs.options, {
                    action_id: false,
                    load_filters: false,
                    toolbar: false,
                });
            },
            resModel: "animal",
            type: "toy",
            viewId: 2,
        });
        assert.hasClass(view.el, "o_toy_view_imp");
        assert.strictEqual(view.el.innerText, "Arch content (id=2)");
    });

    QUnit.test("rendering with given arch attribute 'js_class'", async function (assert) {
        assert.expect(4);
        const view = await makeView({
            serverData,
            mockRPC: (_, args) => {
                assert.deepEqual(args.kwargs.views, [[false, "toy"]]);
                assert.deepEqual(args.kwargs.options, {
                    action_id: false,
                    load_filters: false,
                    toolbar: false,
                });
            },
            resModel: "animal",
            type: "toy",
            arch: `<toy js_class="toy_imp">Specific arch content for specific class</toy>`,
        });
        assert.hasClass(view.el, "o_toy_view_imp");
        assert.strictEqual(view.el.innerText, "Specific arch content for specific class");
    });

    QUnit.test(
        "rendering with loaded arch attribute 'js_class' and given jsClass",
        async function (assert) {
            assert.expect(3);

            class ToyView2 extends Component {}
            ToyView2.template = xml`<div class="o_toy_view_2"/>`;
            ToyView2.type = "toy";
            viewRegistry.add("toy_2", ToyView2);

            const view = await makeView({
                serverData,
                mockRPC: (_, args) => {
                    assert.deepEqual(args.kwargs.views, [[2, "toy"]]);
                    assert.deepEqual(args.kwargs.options, {
                        action_id: false,
                        load_filters: false,
                        toolbar: false,
                    });
                },
                resModel: "animal",
                type: "toy_2",
                viewId: 2,
            });
            assert.hasClass(view.el, "o_toy_view_imp", "jsClass from arch prefered");
        }
    );

    QUnit.test(
        "rendering with given arch attribute 'js_class' and given jsClass",
        async function (assert) {
            assert.expect(3);

            class ToyView2 extends Component {}
            ToyView2.template = xml`<div class="o_toy_view_2"/>`;
            ToyView2.type = "toy";
            viewRegistry.add("toy_2", ToyView2);

            const view = await makeView({
                serverData,
                mockRPC: (_, args) => {
                    assert.deepEqual(args.kwargs.views, [[false, "toy"]]);
                    assert.deepEqual(args.kwargs.options, {
                        action_id: false,
                        load_filters: false,
                        toolbar: false,
                    });
                },
                resModel: "animal",
                type: "toy_2",
                arch: `<toy js_class="toy_imp"/>`,
            });
            assert.hasClass(view.el, "o_toy_view_imp", "jsClass from arch prefered");
        }
    );

    ////////////////////////////////////////////////////////////////////////////
    // props validation
    ////////////////////////////////////////////////////////////////////////////

    QUnit.test("'resModel' must be passed as prop", async function (assert) {
        assert.expect(2);
        try {
            await makeView({ serverData });
        } catch (error) {
            assert.step(error.message);
        }
        assert.verifySteps([`View props should have a "resModel" key`]);
    });

    QUnit.test("'type' must be passed as prop", async function (assert) {
        assert.expect(2);
        try {
            await makeView({ serverData, resModel: "animal" });
        } catch (error) {
            assert.step(error.message);
        }
        assert.verifySteps([`View props should have a "type" key`]);
    });

    ////////////////////////////////////////////////////////////////////////////
    // props
    ////////////////////////////////////////////////////////////////////////////

    QUnit.test(
        "search query props are passed as props to concrete view (default search arch)",
        async function (assert) {
            assert.expect(4);

            class ToyView extends Component {
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
            ToyView.template = xml`<div/>`;
            ToyView.type = "toy";

            viewRegistry.add("toy", ToyView, { force: true });

            await makeView({
                serverData,
                resModel: "animal",
                type: "toy",
                domain: [[0, "=", 1]],
                groupBy: ["birthday"],
                context: { key: "val" },
                orderBy: ["bar"],
            });
        }
    );

    QUnit.test("empty prop 'noContentHelp'", async function (assert) {
        assert.expect(1);

        class ToyView extends Component {
            setup() {
                assert.notOk("noContentHelp" in this.props);
            }
        }
        ToyView.template = xml`<div/>`;
        ToyView.type = "toy";
        viewRegistry.add("toy", ToyView, { force: true });

        await makeView({ serverData, resModel: "animal", type: "toy", noContentHelp: "  " });
    });

    QUnit.test("non empty prop 'noContentHelp'", async function (assert) {
        assert.expect(1);

        class ToyView extends Component {
            setup() {
                assert.strictEqual(this.props.info.noContentHelp, "<div>Help</div>");
            }
        }
        ToyView.template = xml`<div/>`;
        ToyView.type = "toy";
        viewRegistry.add("toy", ToyView, { force: true });

        await makeView({
            serverData,
            resModel: "animal",
            type: "toy",
            noContentHelp: "<div>Help</div>",
        });
    });

    QUnit.test("useSampleModel false by default", async function (assert) {
        assert.expect(1);

        class ToyView extends Component {
            setup() {
                assert.strictEqual(this.props.useSampleModel, false);
            }
        }
        ToyView.template = xml`<div/>`;
        ToyView.type = "toy";
        viewRegistry.add("toy", ToyView, { force: true });

        await makeView({ serverData, resModel: "animal", type: "toy" });
    });

    QUnit.test("sample='1' on arch", async function (assert) {
        assert.expect(1);

        class ToyView extends Component {
            setup() {
                assert.strictEqual(this.props.useSampleModel, true);
            }
        }
        ToyView.template = xml`<div/>`;
        ToyView.type = "toy";
        viewRegistry.add("toy", ToyView, { force: true });

        await makeView({ serverData, resModel: "animal", type: "toy", arch: `<toy sample="1"/>` });
    });

    QUnit.test("sample='0' on arch and useSampleModel=true", async function (assert) {
        assert.expect(1);

        class ToyView extends Component {
            setup() {
                assert.strictEqual(this.props.useSampleModel, true);
            }
        }
        ToyView.template = xml`<div/>`;
        ToyView.type = "toy";
        viewRegistry.add("toy", ToyView, { force: true });

        await makeView({
            serverData,
            resModel: "animal",
            type: "toy",
            useSampleModel: true,
            arch: `<toy sample="0"/>`,
        });
    });

    QUnit.test("sample='1' on arch and useSampleModel=false", async function (assert) {
        assert.expect(1);

        class ToyView extends Component {
            setup() {
                assert.strictEqual(this.props.useSampleModel, false);
            }
        }
        ToyView.template = xml`<div/>`;
        ToyView.type = "toy";
        viewRegistry.add("toy", ToyView, { force: true });

        await makeView({
            serverData,
            resModel: "animal",
            type: "toy",
            useSampleModel: false,
            arch: `<toy sample="1"/>`,
        });
    });

    QUnit.test("useSampleModel=true", async function (assert) {
        assert.expect(1);

        class ToyView extends Component {
            setup() {
                assert.strictEqual(this.props.useSampleModel, true);
            }
        }
        ToyView.template = xml`<div/>`;
        ToyView.type = "toy";
        viewRegistry.add("toy", ToyView, { force: true });

        await makeView({ serverData, resModel: "animal", type: "toy", useSampleModel: true });
    });

    QUnit.test("rendering with given prop", async function (assert) {
        assert.expect(1);

        class ToyView extends Component {
            setup() {
                assert.strictEqual(this.props.specificProp, "specificProp");
            }
        }
        ToyView.template = xml`<div/>`;
        ToyView.type = "toy";
        viewRegistry.add("toy", ToyView, { force: true });

        await makeView({
            serverData,
            resModel: "animal",
            type: "toy",
            specificProp: "specificProp",
        });
    });

    QUnit.test(
        "search query props are passed as props to concrete view (specific search arch)",
        async function (assert) {
            assert.expect(4);

            class ToyView extends Component {
                setup() {
                    const { context, domain, groupBy, orderBy } = this.props;
                    assert.deepEqual(context, {
                        lang: "en",
                        tz: "taht",
                        uid: 7,
                    });
                    assert.deepEqual(domain, ["&", [0, "=", 1], [1, "=", 1]]);
                    assert.deepEqual(groupBy, ["name"]);
                    assert.deepEqual(orderBy, ["bar"]);
                }
            }
            ToyView.template = xml`<div/>`;
            ToyView.type = "toy";
            viewRegistry.add("toy", ToyView, { force: true });

            await makeView({
                serverData,
                type: "toy",
                resModel: "animal",
                searchViewId: 1,
                domain: [[0, "=", 1]],
                groupBy: ["birthday"],
                context: { search_default_filter: 1, search_default_group_by: 1 },
                orderBy: ["bar"],
            });
        }
    );

    ////////////////////////////////////////////////////////////////////////////
    // update props
    ////////////////////////////////////////////////////////////////////////////

    QUnit.test("react to prop 'domain' changes", async function (assert) {
        assert.expect(2);

        class ToyView extends Component {
            willStart() {
                assert.deepEqual(this.props.domain, [["type", "=", "carnivorous"]]);
            }
            willUpdateProps(nextProps) {
                assert.deepEqual(nextProps.domain, [["type", "=", "herbivorous"]]);
            }
        }
        ToyView.template = xml`<div/>`;
        ToyView.type = "toy";
        viewRegistry.add("toy", ToyView, { force: true });

        const env = await makeTestEnv({ serverData });
        const target = getFixture();

        class Parent extends Component {
            setup() {
                this.state = useState({
                    type: "toy",
                    resModel: "animal",
                    domain: [["type", "=", "carnivorous"]],
                });
            }
        }
        Parent.template = xml`<View t-props="state"/>`;
        Parent.components = { View };

        const parent = await mount(Parent, { env, target });

        parent.state.domain = [["type", "=", "herbivorous"]];

        await nextTick();

        parent.destroy();
    });
});
