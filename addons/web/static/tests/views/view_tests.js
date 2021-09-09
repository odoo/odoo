/** @odoo-module **/

import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import {
    click,
    getFixture,
    makeDeferred,
    nextTick,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { setupControlPanelServiceRegistry } from "@web/../tests/search/helpers";
import { makeView } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";
import { OnboardingBanner } from "@web/views/onboarding_banner";
import { View } from "@web/views/view";
import { actionService } from "@web/webclient/actions/action_service";

const { Component, mount, hooks, tags } = owl;
const { useState } = hooks;
const { xml } = tags;

const serviceRegistry = registry.category("services");
const viewRegistry = registry.category("views");

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
        ToyView.components = { Banner: OnboardingBanner };

        class ToyViewImp extends ToyView {
            setup() {
                super.setup();
                this.class = "o_toy_view_imp";
            }
        }

        viewRegistry.add("toy", ToyView);
        viewRegistry.add("toy_imp", ToyViewImp);

        setupControlPanelServiceRegistry();

        const fakeActionService = {
            name: "action",
            start() {
                return {
                    doAction() {},
                };
            },
        };
        serviceRegistry.add("action", fakeActionService, { force: true });
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
                assert.strictEqual(arch, serverData.views["animal,false,toy"]);
                assert.deepEqual(fields, serverData.models.animal.fields);
                assert.strictEqual(info.actionMenus, undefined);
                assert.strictEqual(this.env.config.viewId, false);
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
                assert.strictEqual(arch, serverData.views["animal,1,toy"]);
                assert.deepEqual(fields, serverData.models.animal.fields);
                assert.strictEqual(info.actionMenus, undefined);
                assert.strictEqual(this.env.config.viewId, 1);
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
                assert.strictEqual(arch, serverData.views["animal,1,toy"]);
                assert.deepEqual(fields, serverData.models.animal.fields);
                assert.strictEqual(info.actionMenus, undefined);
                assert.strictEqual(this.env.config.viewId, 1);
            },
        });

        const view = await makeView({
            serverData,
            mockRPC: (_, args) => {
                console.log(_);
                assert.deepEqual(args.kwargs.views, [[1, "toy"]]);
                assert.deepEqual(args.kwargs.options, {
                    action_id: false,
                    load_filters: false,
                    toolbar: false,
                });
            },
            resModel: "animal",
            type: "toy",
            config: {
                views: [[1, "toy"]],
            },
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
                    assert.strictEqual(arch, serverData.views["animal,false,toy"]);
                    assert.deepEqual(fields, serverData.models.animal.fields);
                    assert.strictEqual(info.actionMenus, undefined);
                    assert.strictEqual(this.env.config.viewId, false);
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
                config: {
                    views: [[false, "other"]],
                },
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
                assert.strictEqual(arch, serverData.views["animal,1,toy"]);
                assert.deepEqual(fields, serverData.models.animal.fields);
                assert.strictEqual(info.actionMenus, undefined);
                assert.strictEqual(this.env.config.viewId, 1);
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
            config: {
                views: [
                    [3, "toy"],
                    [false, "other"],
                ],
            },
        });
        assert.hasClass(view.el, "o_toy_view");
        assert.strictEqual(view.el.innerHTML, serverData.views["animal,1,toy"]);
    });

    QUnit.test("rendering with given arch and fields", async function (assert) {
        assert.expect(6);

        const ToyView = viewRegistry.get("toy");
        patchWithCleanup(ToyView.prototype, {
            setup() {
                this._super();
                const { arch, fields, info } = this.props;
                assert.strictEqual(arch, `<toy>Specific arch content</toy>`);
                assert.deepEqual(fields, {});
                assert.strictEqual(info.actionMenus, undefined);
                assert.strictEqual(this.env.config.viewId, undefined);
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
                assert.deepEqual(info.actionMenus, {});
                assert.strictEqual(this.env.config.viewId, false);
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
                    assert.deepEqual(info.actionMenus, {});
                    assert.strictEqual(this.env.config.viewId, false);
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
                    const { arch, fields, info } = this.props;
                    assert.strictEqual(arch, `<toy>Specific arch content</toy>`);
                    assert.deepEqual(fields, {});
                    assert.deepEqual(info.actionMenus, {});
                    assert.strictEqual(this.env.config.viewId, undefined);
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
                const {
                    irFilters,
                    searchViewArch,
                    searchViewFields,
                    searchViewId,
                } = this.props.info;
                assert.strictEqual(searchViewArch, serverData.views["animal,false,search"]);
                assert.deepEqual(searchViewFields, serverData.models.animal.fields);
                assert.strictEqual(searchViewId, false);
                assert.strictEqual(irFilters, undefined);
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
                    const {
                        irFilters,
                        searchViewArch,
                        searchViewFields,
                        searchViewId,
                    } = this.props.info;
                    assert.strictEqual(searchViewArch, `<search/>`);
                    assert.deepEqual(searchViewFields, {});
                    assert.strictEqual(searchViewId, false);
                    assert.strictEqual(irFilters, undefined);
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
        "rendering with given arch, fields, searchViewArch, and searchViewFields",
        async function (assert) {
            assert.expect(6);

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
                    assert.strictEqual(searchViewId, undefined);
                    assert.strictEqual(irFilters, undefined);
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
                    const {
                        irFilters,
                        searchViewArch,
                        searchViewFields,
                        searchViewId,
                    } = this.props.info;
                    assert.strictEqual(searchViewArch, `<search/>`);
                    assert.deepEqual(searchViewFields, {});
                    assert.strictEqual(searchViewId, undefined);
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

    QUnit.test("can click on action-bound links -- 1", async (assert) => {
        assert.expect(5);

        const expectedAction = {
            action: {
                type: "ir.actions.client",
                tag: "someAction",
            },
            options: {},
        };

        const fakeActionService = {
            name: "action",
            start() {
                return {
                    doAction(action, options) {
                        assert.deepEqual(action, expectedAction.action);
                        assert.deepEqual(options, expectedAction.options);
                        return Promise.resolve(true);
                    },
                };
            },
        };
        serviceRegistry.add("action", fakeActionService, { force: true });

        serverData.views["animal,1,toy"] = `
            <toy>
                <a type="action" data-method="setTheControl" data-model="animal" />
            </toy>`;

        const mockRPC = (route) => {
            if (route.includes("setTheControl")) {
                assert.step(route);
                return {
                    type: "ir.actions.client",
                    tag: "someAction",
                };
            }
        };

        const toy = await makeView({
            serverData,
            mockRPC,
            resModel: "animal",
            type: "toy",
            config: {
                views: [[1, "toy"]],
            },
        });

        assert.containsOnce(toy, "a");
        await click(toy.el.querySelector("a"));
        assert.verifySteps(["/web/dataset/call_kw/animal/setTheControl"]);
    });

    QUnit.test("can click on action-bound links -- 2", async (assert) => {
        assert.expect(3);

        const expectedAction = {
            action: "myLittleAction",
            options: {
                additionalContext: {
                    somekey: "somevalue",
                },
            },
        };

        const fakeActionService = {
            name: "action",
            start() {
                return {
                    doAction(action, options) {
                        assert.deepEqual(action, expectedAction.action);
                        assert.deepEqual(options, expectedAction.options);
                        return Promise.resolve(true);
                    },
                };
            },
        };
        serviceRegistry.add("action", fakeActionService, { force: true });

        serverData.views["animal,1,toy"] = `
            <toy>
                <a type="action" name="myLittleAction" data-context="{ &quot;somekey&quot;: &quot;somevalue&quot; }"/>
            </toy>`;

        const toy = await makeView({
            serverData,
            resModel: "animal",
            type: "toy",
            config: {
                views: [[1, "toy"]],
            },
        });

        assert.containsOnce(toy, "a");
        await click(toy.el.querySelector("a"));
    });

    QUnit.test("can click on action-bound links -- 3", async (assert) => {
        assert.expect(3);

        const expectedAction = {
            action: {
                domain: [["field", "=", "val"]],
                name: "myTitle",
                res_id: 66,
                res_model: "animal",
                target: "current",
                type: "ir.actions.act_window",
                views: [[55, "toy"]],
            },
            options: {
                additionalContext: {
                    somekey: "somevalue",
                },
            },
        };

        const fakeActionService = {
            name: "action",
            start() {
                return {
                    doAction(action, options) {
                        assert.deepEqual(action, expectedAction.action);
                        assert.deepEqual(options, expectedAction.options);
                        return Promise.resolve(true);
                    },
                };
            },
        };
        serviceRegistry.add("action", fakeActionService, { force: true });

        serverData.views["animal,1,toy"] = `
            <toy>
                <a type="action" title="myTitle" data-model="animal" data-resId="66" data-views="[[55, 'toy']]" data-domain="[['field', '=', 'val']]" data-context="{ &quot;somekey&quot;: &quot;somevalue&quot; }"/>
            </toy>`;

        const toy = await makeView({
            serverData,
            resModel: "animal",
            type: "toy",
            config: {
                views: [[1, "toy"]],
            },
        });

        assert.containsOnce(toy, "a");
        await click(toy.el.querySelector("a"));
    });

    QUnit.test("renders banner_route", async (assert) => {
        assert.expect(3);
        serverData.views["animal,1,toy"] = `
            <toy banner_route="/mybody/isacage">
                <Banner t-if="env.config.bannerRoute" />
            </toy>`;

        const mockRPC = (route) => {
            if (route === "/mybody/isacage") {
                assert.step(route);
                return { html: `<div class="setmybodyfree">myBanner</div>` };
            }
        };

        const toy = await makeView({
            serverData,
            mockRPC,
            resModel: "animal",
            type: "toy",
            config: {
                views: [[1, "toy"]],
            },
        });

        assert.verifySteps(["/mybody/isacage"]);
        assert.containsOnce(toy, ".setmybodyfree");
    });

    QUnit.test("renders banner_route with js and css assets", async (assert) => {
        assert.expect(7);
        serverData.views["animal,1,toy"] = `
            <toy banner_route="/mybody/isacage">
                <Banner t-if="env.config.bannerRoute" />
            </toy>`;

        const bannerArch = `
            <div class="setmybodyfree">
                <link rel="stylesheet" href="/mystyle" />
                <script type="text/javascript" src="/myscript" />
                myBanner
            </div>`;

        const mockRPC = (route) => {
            if (route === "/mybody/isacage") {
                assert.step(route);
                return { html: bannerArch };
            }
        };

        const docCreateElement = document.createElement.bind(document);
        const createElement = (tagName) => {
            const elem = docCreateElement(tagName);
            if (tagName === "link") {
                Object.defineProperty(elem, "href", {
                    set(href) {
                        if (href.includes("/mystyle")) {
                            assert.step("css loaded");
                        }
                        Promise.resolve().then(() => elem.dispatchEvent(new Event("load")));
                    },
                });
            } else if (tagName === "script") {
                Object.defineProperty(elem, "src", {
                    set(src) {
                        if (src.includes("/myscript")) {
                            assert.step("js loaded");
                        }
                        Promise.resolve().then(() => elem.dispatchEvent(new Event("load")));
                    },
                });
            }
            return elem;
        };

        patchWithCleanup(document, { createElement });

        const toy = await makeView({
            serverData,
            mockRPC,
            resModel: "animal",
            type: "toy",
            config: {
                views: [[1, "toy"]],
            },
        });

        assert.verifySteps(["/mybody/isacage", "js loaded", "css loaded"]);
        assert.containsOnce(toy, ".setmybodyfree");
        assert.containsNone(toy, "script");
        assert.containsNone(toy, "link");
    });

    QUnit.test("banner can re-render with new HTML", async (assert) => {
        assert.expect(10);
        assert.expect(8);

        serviceRegistry.add("action", actionService, { force: true });

        serverData.views["animal,1,toy"] = `
            <toy banner_route="/mybody/isacage">
                <Banner t-if="env.config.bannerRoute" />
            </toy>`;

        const banners = [
            `<div class="banner1">
                <a type="action" data-method="setTheControl" data-model="animal" data-reload-on-close="true" />
            </div>`,
            `<div class="banner2">
                MyBanner
            /div>`,
        ];
        const mockRPC = async (route) => {
            if (route === "/mybody/isacage") {
                assert.step(route);
                return { html: banners.shift() };
            }
            if (route.includes("setTheControl")) {
                return {
                    type: "ir.actions.act_window_close",
                };
            }
        };

        const toy = await makeView({
            serverData,
            mockRPC,
            resModel: "animal",
            type: "toy",
            config: {
                views: [[1, "toy"]],
            },
        });

        assert.verifySteps(["/mybody/isacage"]);
        assert.containsOnce(toy, ".banner1");
        assert.containsNone(toy, ".banner2");
        await click(toy.el.querySelector("a"));
        assert.verifySteps(["/mybody/isacage"]);
        assert.containsNone(toy, ".banner1");
        assert.containsOnce(toy, ".banner2");
    });

    QUnit.test("banner does not reload on render", async (assert) => {
        assert.expect(5);
        serverData.views["animal,1,toy"] = `
            <toy banner_route="/mybody/isacage">
                <Banner t-if="env.config.bannerRoute" />
            </toy>`;

        const bannerArch = `
            <div class="setmybodyfree">
                myBanner
            </div>`;

        const mockRPC = (route) => {
            if (route === "/mybody/isacage") {
                assert.step(route);
                return { html: bannerArch };
            }
        };

        const toy = await makeView({
            serverData,
            mockRPC,
            resModel: "animal",
            type: "toy",
            config: {
                views: [[1, "toy"]],
            },
        });

        assert.verifySteps(["/mybody/isacage"]);
        assert.containsOnce(toy, ".setmybodyfree");
        await toy.render();
        await nextTick();
        assert.verifySteps([]);
        assert.containsOnce(toy, ".setmybodyfree");
    });

    QUnit.test("click on action-bound links in banner (concurrency)", async (assert) => {
        assert.expect(1);

        const prom = makeDeferred();

        const expectedAction = {
            type: "ir.actions.client",
            tag: "gout",
        };

        const fakeActionService = {
            name: "action",
            start() {
                return {
                    doAction(action) {
                        assert.deepEqual(action, expectedAction);
                        return Promise.resolve(true);
                    },
                };
            },
        };
        serviceRegistry.add("action", fakeActionService, { force: true });

        serverData.views["animal,1,toy"] = `
            <toy banner_route="/banner_route">
                <Banner t-if="env.config.bannerRoute" />
                <a type="action" data-method="setTheControl" data-model="animal" />
            </toy>`;

        const mockRPC = async (route) => {
            if (route.includes("banner_route")) {
                return {
                    html: `<div><a type="action" data-method="heartOfTheSun" data-model="animal" /></div>`,
                };
            }
            if (route.includes("setTheControl")) {
                await prom;
                return {
                    type: "ir.actions.client",
                    tag: "toug",
                };
            }
            if (route.includes("heartOfTheSun")) {
                return {
                    type: "ir.actions.client",
                    tag: "gout",
                };
            }
        };

        const toy = await makeView({
            mockRPC,
            serverData,
            resModel: "animal",
            type: "toy",
            config: {
                views: [[1, "toy"]],
            },
        });

        await click(toy.el.querySelector("a[data-method='setTheControl']"));
        click(toy.el.querySelector("a[data-method='heartOfTheSun']"));
        prom.resolve();
        await nextTick();
    });

    QUnit.test("real life banner", async (assert) => {
        assert.expect(10);

        serverData.views["animal,1,toy"] = `
            <toy banner_route="/mybody/isacage">
                <Banner t-if="env.config.bannerRoute" />
            </toy>`;

        const bannerArch = `
            <div class="modal o_onboarding_modal o_technical_modal" tabindex="-1" role="dialog">
                <div class="modal-dialog" role="document">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Remove Configuration Tips</h5>
                            <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                                <span aria-label="Close">×</span>
                            </button>
                        </div>
                        <div class="modal-body">
                            <p>Do you want to remove this configuration panel?</p>
                        </div>
                        <div class="modal-footer">
                            <a type="action" class="btn btn-primary" data-dismiss="modal" data-toggle="collapse" href=".o_onboarding_container" data-model="mah.model" data-method="mah_method">Remove</a>
                            <button type="button" class="btn btn-secondary" data-dismiss="modal">Discard</button>
                        </div>
                    </div>
                </div>
            </div>
            <div class="o_onboarding_container collapse show">
                <div class="o_onboarding" />
                    <div class="o_onboarding_wrap" />
                        <a href="#" data-toggle="modal" data-target=".o_onboarding_modal" class="float-right o_onboarding_btn_close">
                            <i class="fa fa-times" title="Close the onboarding panel" id="closeOnboarding"></i>
                        </a>
                        <div class="bannerContent">Content</div>
                    </div>
                </div>
            </div>`;

        const mockRPC = (route, args) => {
            if (route === "/mybody/isacage") {
                assert.step(route);
                return { html: bannerArch };
            }
            if (args.method === "mah_method") {
                assert.step(args.method);
                return true;
            }
        };

        const toy = await makeView({
            serverData,
            mockRPC,
            resModel: "animal",
            type: "toy",
            config: {
                views: [[1, "toy"]],
            },
        });

        const prom = new Promise((resolve) => {
            const complete = (ev) => {
                if (ev.target.classList.contains("o_onboarding_container")) {
                    resolve();
                }
            };
            // We need to handle both events, because the transition is not
            // always executed
            toy.el.addEventListener("transitionend", complete);
            toy.el.addEventListener("transitioncancel", complete);
        });

        assert.verifySteps(["/mybody/isacage"]);
        assert.isNotVisible(toy.el.querySelector(".modal"));
        assert.hasClass(toy.el.querySelector(".o_onboarding_container"), "collapse show");

        await click(toy.el.querySelector("#closeOnboarding"));
        assert.isVisible(toy.el.querySelector(".modal"));

        await click(toy.el.querySelector(".modal a[type='action']"));
        assert.verifySteps(["mah_method"]);
        await prom;
        assert.doesNotHaveClass(toy.el.querySelector(".o_onboarding_container"), "show");
        assert.hasClass(toy.el.querySelector(".o_onboarding_container"), "collapse");
        assert.isNotVisible(toy.el.querySelector(".modal"));
    });

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
        assert.expect(2);
        const view = await makeView({
            serverData,
            mockRPC: () => {
                throw new Error("no RPC expected");
            },
            resModel: "animal",
            type: "toy",
            arch: `<toy js_class="toy_imp">Specific arch content for specific class</toy>`,
            fields: {},
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
            assert.expect(1);

            class ToyView2 extends Component {}
            ToyView2.template = xml`<div class="o_toy_view_2"/>`;
            ToyView2.type = "toy";
            viewRegistry.add("toy_2", ToyView2);

            const view = await makeView({
                serverData,
                mockRPC: () => {
                    throw new Error("no RPC expected");
                },
                resModel: "animal",
                type: "toy_2",
                arch: `<toy js_class="toy_imp"/>`,
                fields: {},
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
            await makeView({ serverData }, { noFields: true });
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

    QUnit.test("'arch' cannot be passed as prop alone", async function (assert) {
        assert.expect(2);
        try {
            await makeView(
                { serverData, resModel: "animal", type: "toy", arch: "<toy/>" },
                { noFields: true }
            );
        } catch (error) {
            assert.step(error.message);
        }
        assert.verifySteps([`"arch" and "fields" props must be given together`]);
    });

    QUnit.test("'fields' cannot be passed as prop alone", async function (assert) {
        assert.expect(2);
        try {
            await makeView({ serverData, resModel: "animal", type: "toy", fields: {} });
        } catch (error) {
            assert.step(error.message);
        }
        assert.verifySteps([`"arch" and "fields" props must be given together`]);
    });

    QUnit.test("'searchViewArch' cannot be passed as prop alone", async function (assert) {
        assert.expect(2);
        try {
            await makeView({
                serverData,
                resModel: "animal",
                type: "toy",
                searchViewArch: "<toy/>",
            });
        } catch (error) {
            assert.step(error.message);
        }
        assert.verifySteps([
            `"searchViewArch" and "searchViewFields" props must be given together`,
        ]);
    });

    QUnit.test("'searchViewFields' cannot be passed as prop alone", async function (assert) {
        assert.expect(2);
        try {
            await makeView({ serverData, resModel: "animal", type: "toy", searchViewFields: {} });
        } catch (error) {
            assert.step(error.message);
        }
        assert.verifySteps([
            `"searchViewArch" and "searchViewFields" props must be given together`,
        ]);
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
                assert.strictEqual(this.props.info.noContentHelp, undefined);
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

        await makeView({
            serverData,
            resModel: "animal",
            type: "toy",
            arch: `<toy sample="1"/>`,
            fields: {},
        });
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
            fields: {},
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
            fields: {},
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
