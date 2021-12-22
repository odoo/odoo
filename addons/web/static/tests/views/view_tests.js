/** @odoo-module **/

import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import {
    click,
    getFixture,
    makeDeferred,
    mount,
    nextTick,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { setupControlPanelServiceRegistry } from "@web/../tests/search/helpers";
import { registry } from "@web/core/registry";
import { OnboardingBanner } from "@web/views/onboarding_banner";
import { View } from "@web/views/view";
import { actionService } from "@web/webclient/actions/action_service";

const { Component, onWillStart, onWillUpdateProps, useState, xml } = owl;

const serviceRegistry = registry.category("services");
const viewRegistry = registry.category("views");

let serverData;
let target;

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

        class ToyController extends Component {
            setup() {
                this.class = "toy";
                this.template = xml`${this.props.arch}`;
            }
        }
        ToyController.template = xml`<div t-attf-class="{{class}} {{props.className}}"><t t-call="{{ template }}"/></div>`;
        ToyController.components = { Banner: OnboardingBanner };

        const toyView = {
            type: "toy",
            Controller: ToyController,
        };

        class ToyControllerImp extends ToyController {
            setup() {
                super.setup();
                this.class = "toy_imp";
            }
        }

        viewRegistry.add("toy", toyView);
        viewRegistry.add("toy_imp", { ...toyView, Controller: ToyControllerImp });

        setupViewRegistries();
        const fakeActionService = {
            name: "action",
            start() {
                return {
                    doAction() {},
                };
            },
        };
        serviceRegistry.add("action", fakeActionService, { force: true });

        target = getFixture();
    });

    QUnit.module("View component");

    ////////////////////////////////////////////////////////////////////////////
    // get_views
    ////////////////////////////////////////////////////////////////////////////

    QUnit.test("simple rendering", async function (assert) {
        assert.expect(10);

        const ToyController = viewRegistry.get("toy").Controller;
        patchWithCleanup(ToyController.prototype, {
            setup() {
                this._super();
                const { arch, fields, info } = this.props;
                assert.strictEqual(arch, serverData.views["animal,false,toy"]);
                assert.deepEqual(fields, serverData.models.animal.fields);
                assert.strictEqual(info.actionMenus, undefined);
                assert.strictEqual(this.env.config.viewId, false);
            },
        });

        const mockRPC = (_, args) => {
            assert.strictEqual(args.model, "animal");
            assert.strictEqual(args.method, "get_views");
            assert.deepEqual(args.kwargs.views, [[false, "toy"]]);
            assert.deepEqual(args.kwargs.options, {
                action_id: false,
                load_filters: false,
                toolbar: false,
            });
        };
        const env = await makeTestEnv({ serverData, mockRPC });
        const props = {
            resModel: "animal",
            type: "toy",
        };
        await mount(View, target, { env, props });
        assert.containsOnce(target, ".o_toy_view.o_view_controller");
        assert.strictEqual(
            target.querySelector(".o_toy_view.toy").innerHTML,
            serverData.views["animal,false,toy"]
        );
    });

    QUnit.test("rendering with given viewId", async function (assert) {
        assert.expect(8);

        const ToyController = viewRegistry.get("toy").Controller;
        patchWithCleanup(ToyController.prototype, {
            setup() {
                this._super();
                const { arch, fields, info } = this.props;
                assert.strictEqual(arch, serverData.views["animal,1,toy"]);
                assert.deepEqual(fields, serverData.models.animal.fields);
                assert.strictEqual(info.actionMenus, undefined);
                assert.strictEqual(this.env.config.viewId, 1);
            },
        });

        const mockRPC = (_, args) => {
            assert.deepEqual(args.kwargs.views, [[1, "toy"]]);
            assert.deepEqual(args.kwargs.options, {
                action_id: false,
                load_filters: false,
                toolbar: false,
            });
        };
        const env = await makeTestEnv({ serverData, mockRPC });
        const props = {
            resModel: "animal",
            type: "toy",
            viewId: 1,
        };
        await mount(View, target, { env, props });
        assert.containsOnce(target, ".o_toy_view");
        assert.strictEqual(
            target.querySelector(".o_toy_view.toy").innerHTML,
            serverData.views["animal,1,toy"]
        );
    });

    QUnit.test("rendering with given 'views' param", async function (assert) {
        assert.expect(8);

        const ToyController = viewRegistry.get("toy").Controller;
        patchWithCleanup(ToyController.prototype, {
            setup() {
                this._super();
                const { arch, fields, info } = this.props;
                assert.strictEqual(arch, serverData.views["animal,1,toy"]);
                assert.deepEqual(fields, serverData.models.animal.fields);
                assert.strictEqual(info.actionMenus, undefined);
                assert.strictEqual(this.env.config.viewId, 1);
            },
        });

        const mockRPC = (_, args) => {
            assert.deepEqual(args.kwargs.views, [[1, "toy"]]);
            assert.deepEqual(args.kwargs.options, {
                action_id: false,
                load_filters: false,
                toolbar: false,
            });
        };
        const config = {
            views: [[1, "toy"]],
        };
        const env = await makeTestEnv({ serverData, mockRPC, config });
        const props = {
            resModel: "animal",
            type: "toy",
        };
        await mount(View, target, { env, props });
        assert.containsOnce(target, ".o_toy_view");
        assert.strictEqual(
            target.querySelector(".o_toy_view.toy").innerHTML,
            serverData.views["animal,1,toy"]
        );
    });

    QUnit.test(
        "rendering with given 'views' param not containing view id",
        async function (assert) {
            assert.expect(8);

            const ToyController = viewRegistry.get("toy").Controller;
            patchWithCleanup(ToyController.prototype, {
                setup() {
                    this._super();
                    const { arch, fields, info } = this.props;
                    assert.strictEqual(arch, serverData.views["animal,false,toy"]);
                    assert.deepEqual(fields, serverData.models.animal.fields);
                    assert.strictEqual(info.actionMenus, undefined);
                    assert.strictEqual(this.env.config.viewId, false);
                },
            });

            const mockRPC = (_, args) => {
                assert.deepEqual(args.kwargs.views, [
                    [false, "other"],
                    [false, "toy"],
                ]);
                assert.deepEqual(args.kwargs.options, {
                    action_id: false,
                    load_filters: false,
                    toolbar: false,
                });
            };
            const config = {
                views: [[false, "other"]],
            };
            const env = await makeTestEnv({ serverData, mockRPC, config });
            const props = {
                resModel: "animal",
                type: "toy",
            };
            await mount(View, target, { env, props });
            assert.containsOnce(target, ".o_toy_view");
            assert.strictEqual(
                target.querySelector(".o_toy_view.toy").innerHTML,
                serverData.views["animal,false,toy"]
            );
        }
    );

    QUnit.test("viewId defined as prop and in 'views' prop", async function (assert) {
        assert.expect(8);

        const ToyController = viewRegistry.get("toy").Controller;
        patchWithCleanup(ToyController.prototype, {
            setup() {
                this._super();
                const { arch, fields, info } = this.props;
                assert.strictEqual(arch, serverData.views["animal,1,toy"]);
                assert.deepEqual(fields, serverData.models.animal.fields);
                assert.strictEqual(info.actionMenus, undefined);
                assert.strictEqual(this.env.config.viewId, 1);
            },
        });

        const mockRPC = (_, args) => {
            assert.deepEqual(args.kwargs.views, [
                [1, "toy"],
                [false, "other"],
            ]);
            assert.deepEqual(args.kwargs.options, {
                action_id: false,
                load_filters: false,
                toolbar: false,
            });
        };
        const config = {
            views: [
                [3, "toy"],
                [false, "other"],
            ],
        };
        const env = await makeTestEnv({ serverData, mockRPC, config });
        const props = {
            resModel: "animal",
            type: "toy",
            viewId: 1,
        };
        await mount(View, target, { env, props });
        assert.containsOnce(target, ".o_toy_view");
        assert.strictEqual(
            target.querySelector(".o_toy_view.toy").innerHTML,
            serverData.views["animal,1,toy"]
        );
    });

    QUnit.test("rendering with given arch and fields", async function (assert) {
        assert.expect(6);

        const ToyController = viewRegistry.get("toy").Controller;
        patchWithCleanup(ToyController.prototype, {
            setup() {
                this._super();
                const { arch, fields, info } = this.props;
                assert.strictEqual(arch, `<toy>Specific arch content</toy>`);
                assert.deepEqual(fields, {});
                assert.strictEqual(info.actionMenus, undefined);
                assert.strictEqual(this.env.config.viewId, undefined);
            },
        });

        const mockRPC = () => {
            throw new Error("no RPC expected");
        };
        const env = await makeTestEnv({ serverData, mockRPC });
        const props = {
            resModel: "animal",
            type: "toy",
            arch: `<toy>Specific arch content</toy>`,
            fields: {},
        };
        await mount(View, target, { env, props });
        assert.containsOnce(target, ".o_toy_view");
        assert.strictEqual(
            target.querySelector(".o_toy_view.toy").innerHTML,
            `<toy>Specific arch content</toy>`
        );
    });

    QUnit.test("rendering with loadActionMenus='true'", async function (assert) {
        assert.expect(8);

        const ToyController = viewRegistry.get("toy").Controller;
        patchWithCleanup(ToyController.prototype, {
            setup() {
                this._super();
                const { arch, fields, info } = this.props;
                assert.strictEqual(arch, serverData.views["animal,false,toy"]);
                assert.deepEqual(fields, serverData.models.animal.fields);
                assert.deepEqual(info.actionMenus, {});
                assert.strictEqual(this.env.config.viewId, false);
            },
        });

        const mockRPC = (_, args) => {
            // the rpc is done for fields
            assert.deepEqual(args.kwargs.views, [[false, "toy"]]);
            assert.deepEqual(args.kwargs.options, {
                action_id: false,
                load_filters: false,
                toolbar: true,
            });
        };
        const env = await makeTestEnv({ serverData, mockRPC });
        const props = {
            resModel: "animal",
            type: "toy",
            loadActionMenus: true,
        };
        await mount(View, target, { env, props });
        assert.containsOnce(target, ".o_toy_view");
        assert.strictEqual(
            target.querySelector(".o_toy_view.toy").innerHTML,
            serverData.views["animal,false,toy"]
        );
    });

    QUnit.test(
        "rendering with given arch, fields, and loadActionMenus='true'",
        async function (assert) {
            assert.expect(8);

            const ToyController = viewRegistry.get("toy").Controller;
            patchWithCleanup(ToyController.prototype, {
                setup() {
                    this._super();
                    const { arch, fields, info } = this.props;
                    assert.strictEqual(arch, `<toy>Specific arch content</toy>`);
                    assert.deepEqual(fields, {});
                    assert.deepEqual(info.actionMenus, {});
                    assert.strictEqual(this.env.config.viewId, false);
                },
            });

            const mockRPC = (_, args) => {
                // the rpc is done for fields
                assert.deepEqual(args.kwargs.views, [[false, "toy"]]);
                assert.deepEqual(args.kwargs.options, {
                    action_id: false,
                    load_filters: false,
                    toolbar: true,
                });
            };
            const env = await makeTestEnv({ serverData, mockRPC });
            const props = {
                resModel: "animal",
                type: "toy",
                arch: `<toy>Specific arch content</toy>`,
                fields: {},
                loadActionMenus: true,
            };
            await mount(View, target, { env, props });
            assert.containsOnce(target, ".o_toy_view");
            assert.strictEqual(
                target.querySelector(".o_toy_view.toy").innerHTML,
                `<toy>Specific arch content</toy>`
            );
        }
    );

    QUnit.test(
        "rendering with given arch, fields, actionMenus, and loadActionMenus='true'",
        async function (assert) {
            assert.expect(6);

            const ToyController = viewRegistry.get("toy").Controller;
            patchWithCleanup(ToyController.prototype, {
                setup() {
                    this._super();
                    const { arch, fields, info } = this.props;
                    assert.strictEqual(arch, `<toy>Specific arch content</toy>`);
                    assert.deepEqual(fields, {});
                    assert.deepEqual(info.actionMenus, {});
                    assert.strictEqual(this.env.config.viewId, undefined);
                },
            });

            const mockRPC = () => {
                throw new Error("no RPC expected");
            };
            const env = await makeTestEnv({ serverData, mockRPC });
            const props = {
                resModel: "animal",
                type: "toy",
                arch: `<toy>Specific arch content</toy>`,
                fields: {},
                loadActionMenus: true,
                actionMenus: {},
            };
            await mount(View, target, { env, props });
            assert.containsOnce(target, ".o_toy_view");
            assert.strictEqual(
                target.querySelector(".o_toy_view.toy").innerHTML,
                `<toy>Specific arch content</toy>`
            );
        }
    );

    QUnit.test("rendering with given searchViewId", async function (assert) {
        assert.expect(8);

        const ToyController = viewRegistry.get("toy").Controller;
        patchWithCleanup(ToyController.prototype, {
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

        const mockRPC = (_, args) => {
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
        };
        const env = await makeTestEnv({ serverData, mockRPC });
        const props = {
            resModel: "animal",
            type: "toy",
            searchViewId: false,
        };
        await mount(View, target, { env, props });
        assert.containsOnce(target, ".o_toy_view");
        assert.strictEqual(
            target.querySelector(".o_toy_view").innerText,
            "Arch content (id=false)"
        );
    });

    QUnit.test(
        "rendering with given arch, fields, searchViewId, searchViewArch, and searchViewFields",
        async function (assert) {
            assert.expect(6);

            const ToyController = viewRegistry.get("toy").Controller;
            patchWithCleanup(ToyController.prototype, {
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

            const mockRPC = () => {
                throw new Error("no RPC expected");
            };
            const env = await makeTestEnv({ serverData, mockRPC });
            const props = {
                resModel: "animal",
                type: "toy",
                arch: `<toy>Specific arch content</toy>`,
                fields: {},
                searchViewId: false,
                searchViewArch: `<search/>`,
                searchViewFields: {},
            };
            await mount(View, target, { env, props });
            assert.containsOnce(target, ".o_toy_view");
            assert.strictEqual(
                target.querySelector(".o_toy_view").innerText,
                "Specific arch content"
            );
        }
    );

    QUnit.test(
        "rendering with given arch, fields, searchViewArch, and searchViewFields",
        async function (assert) {
            assert.expect(6);

            const ToyController = viewRegistry.get("toy").Controller;
            patchWithCleanup(ToyController.prototype, {
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

            const mockRPC = () => {
                throw new Error("no RPC expected");
            };
            const env = await makeTestEnv({ serverData, mockRPC });
            const props = {
                resModel: "animal",
                type: "toy",
                arch: `<toy>Specific arch content</toy>`,
                fields: {},
                searchViewArch: `<search/>`,
                searchViewFields: {},
            };
            await mount(View, target, { env, props });
            assert.containsOnce(target, ".o_toy_view");
            assert.strictEqual(
                target.querySelector(".o_toy_view").innerText,
                "Specific arch content"
            );
        }
    );

    QUnit.test(
        "rendering with given arch, fields, searchViewId, searchViewArch, searchViewFields, and loadIrFilters='true'",
        async function (assert) {
            assert.expect(8);

            const ToyController = viewRegistry.get("toy").Controller;
            patchWithCleanup(ToyController.prototype, {
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

            const mockRPC = (_, args) => {
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
            };
            const env = await makeTestEnv({ serverData, mockRPC });
            const props = {
                resModel: "animal",
                type: "toy",
                arch: `<toy>Specific arch content</toy>`,
                fields: {},
                searchViewId: false,
                searchViewArch: `<search/>`,
                searchViewFields: {},
                loadIrFilters: true,
            };
            await mount(View, target, { env, props });
            assert.containsOnce(target, ".o_toy_view");
            assert.strictEqual(
                target.querySelector(".o_toy_view").innerText,
                "Specific arch content"
            );
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

            const ToyController = viewRegistry.get("toy").Controller;
            patchWithCleanup(ToyController.prototype, {
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

            const mockRPC = () => {
                throw new Error("no RPC expected");
            };
            const env = await makeTestEnv({ serverData, mockRPC });
            const props = {
                resModel: "animal",
                type: "toy",
                arch: `<toy>Specific arch content</toy>`,
                fields: {},
                searchViewArch: `<search/>`,
                searchViewFields: {},
                loadIrFilters: true,
                irFilters,
            };
            await mount(View, target, { env, props });
            assert.containsOnce(target, ".o_toy_view");
            assert.strictEqual(
                target.querySelector(".o_toy_view").innerText,
                "Specific arch content"
            );
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
        const config = {
            views: [[1, "toy"]],
        };
        const env = await makeTestEnv({ serverData, mockRPC, config });
        const props = {
            resModel: "animal",
            type: "toy",
        };
        await mount(View, target, { env, props });

        assert.containsOnce(target, "a");
        await click(target.querySelector("a"));
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

        const config = {
            views: [[1, "toy"]],
        };
        const env = await makeTestEnv({ serverData, config });
        const props = {
            resModel: "animal",
            type: "toy",
        };
        await mount(View, target, { env, props });

        assert.containsOnce(target, "a");
        await click(target.querySelector("a"));
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

        const config = {
            views: [[1, "toy"]],
        };
        const env = await makeTestEnv({ serverData, config });
        const props = {
            resModel: "animal",
            type: "toy",
        };
        await mount(View, target, { env, props });

        assert.containsOnce(target, "a");
        await click(target.querySelector("a"));
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
        const config = {
            views: [[1, "toy"]],
        };
        const env = await makeTestEnv({ serverData, mockRPC, config });
        const props = {
            resModel: "animal",
            type: "toy",
        };
        await mount(View, target, { env, props });

        assert.verifySteps(["/mybody/isacage"]);
        assert.containsOnce(target, ".setmybodyfree");
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

        const config = {
            views: [[1, "toy"]],
        };
        const env = await makeTestEnv({ serverData, mockRPC, config });
        const props = {
            resModel: "animal",
            type: "toy",
        };
        await mount(View, target, { env, props });

        assert.verifySteps(["/mybody/isacage", "js loaded", "css loaded"]);
        assert.containsOnce(target, ".setmybodyfree");
        assert.containsNone(target, "script");
        assert.containsNone(target, "link");
    });

    QUnit.test("banner can re-render with new HTML", async (assert) => {
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
        const config = {
            views: [[1, "toy"]],
        };
        const env = await makeTestEnv({ serverData, mockRPC, config });
        const props = {
            resModel: "animal",
            type: "toy",
        };
        await mount(View, target, { env, props });

        assert.verifySteps(["/mybody/isacage"]);
        assert.containsOnce(target, ".banner1");
        assert.containsNone(target, ".banner2");
        await click(target.querySelector("a"));
        assert.verifySteps(["/mybody/isacage"]);
        assert.containsNone(target, ".banner1");
        assert.containsOnce(target, ".banner2");
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

        let toy;
        const toyView = viewRegistry.get("toy");
        class ToyViewExtendedController extends toyView.Controller {
            setup() {
                super.setup();
                toy = this;
            }
        }
        viewRegistry.add(
            "toy",
            { ...toyView, Controller: ToyViewExtendedController },
            { force: true }
        );

        const mockRPC = (route) => {
            if (route === "/mybody/isacage") {
                assert.step(route);
                return { html: bannerArch };
            }
        };
        const config = {
            views: [[1, "toy"]],
        };
        const env = await makeTestEnv({ serverData, mockRPC, config });
        const props = {
            resModel: "animal",
            type: "toy",
        };
        await mount(View, target, { env, props });

        assert.verifySteps(["/mybody/isacage"]);
        assert.containsOnce(target, ".setmybodyfree");
        await toy.render();
        await nextTick();
        assert.verifySteps([]);
        assert.containsOnce(target, ".setmybodyfree");
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
        const config = {
            views: [[1, "toy"]],
        };
        const env = await makeTestEnv({ serverData, mockRPC, config });
        const props = {
            resModel: "animal",
            type: "toy",
        };
        await mount(View, target, { env, props });

        await click(target.querySelector("a[data-method='setTheControl']"));
        click(target.querySelector("a[data-method='heartOfTheSun']"));
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
        const config = {
            views: [[1, "toy"]],
        };
        const env = await makeTestEnv({ serverData, mockRPC, config });
        const props = {
            resModel: "animal",
            type: "toy",
        };
        await mount(View, target, { env, props });

        const prom = new Promise((resolve) => {
            const complete = (ev) => {
                if (ev.target.classList.contains("o_onboarding_container")) {
                    resolve();
                }
            };
            // We need to handle both events, because the transition is not
            // always executed
            target.addEventListener("transitionend", complete);
            target.addEventListener("transitioncancel", complete);
        });

        assert.verifySteps(["/mybody/isacage"]);
        assert.isNotVisible(target.querySelector(".modal"));
        assert.hasClass(target.querySelector(".o_onboarding_container"), "collapse show");

        await click(target.querySelector("#closeOnboarding"));
        assert.isVisible(target.querySelector(".modal"));

        await click(target.querySelector(".modal a[type='action']"));
        assert.verifySteps(["mah_method"]);
        await prom;
        assert.doesNotHaveClass(target.querySelector(".o_onboarding_container"), "show");
        assert.hasClass(target.querySelector(".o_onboarding_container"), "collapse");
        assert.isNotVisible(target.querySelector(".modal"));
    });

    ////////////////////////////////////////////////////////////////////////////
    // js_class
    ////////////////////////////////////////////////////////////////////////////

    QUnit.test("rendering with given jsClass", async function (assert) {
        assert.expect(4);
        const mockRPC = (_, args) => {
            assert.deepEqual(args.kwargs.views, [[false, "toy"]]);
            assert.deepEqual(args.kwargs.options, {
                action_id: false,
                load_filters: false,
                toolbar: false,
            });
        };
        const env = await makeTestEnv({ serverData, mockRPC });
        const props = {
            resModel: "animal",
            type: "toy_imp",
        };
        await mount(View, target, { env, props });
        assert.containsOnce(target, ".o_toy_view.toy_imp");
        assert.strictEqual(
            target.querySelector(".o_toy_view.toy_imp").innerText,
            "Arch content (id=false)"
        );
    });

    QUnit.skip("rendering with loaded arch attribute 'js_class'", async function (assert) {
        assert.expect(4);
        const mockRPC = (_, args) => {
            assert.deepEqual(args.kwargs.views, [[2, "toy"]]);
            assert.deepEqual(args.kwargs.options, {
                action_id: false,
                load_filters: false,
                toolbar: false,
            });
        };
        const env = await makeTestEnv({ serverData, mockRPC });
        const props = {
            resModel: "animal",
            type: "toy",
            viewId: 2,
        };
        await mount(View, target, { env, props });
        assert.containsOnce(target, ".o_toy_view.toy_imp");
        assert.strictEqual(
            target.querySelector(".o_toy_view.toy_imp").innerText,
            "Arch content (id=2)"
        );
    });

    QUnit.skip("rendering with given arch attribute 'js_class'", async function (assert) {
        const mockRPC = () => {
            throw new Error("no RPC expected");
        };
        const env = await makeTestEnv({ serverData, mockRPC });
        const props = {
            resModel: "animal",
            type: "toy",
            arch: `<toy js_class="toy_imp">Specific arch content for specific class</toy>`,
            fields: {},
        };
        await mount(View, target, { env, props });
        assert.containsOnce(target, ".o_toy_view.toy_imp");
        assert.strictEqual(
            target.querySelector(".o_toy_view.toy_imp").innerText,
            "Specific arch content for specific class"
        );
    });

    QUnit.skip(
        "rendering with loaded arch attribute 'js_class' and given jsClass",
        async function (assert) {
            assert.expect(3);

            class ToyView2 extends Component {}
            ToyView2.template = xml`<div class="o_toy_view_2"/>`;
            ToyView2.type = "toy";
            viewRegistry.add("toy_2", ToyView2);

            const mockRPC = (_, args) => {
                assert.deepEqual(args.kwargs.views, [[2, "toy"]]);
                assert.deepEqual(args.kwargs.options, {
                    action_id: false,
                    load_filters: false,
                    toolbar: false,
                });
            };
            const env = await makeTestEnv({ serverData, mockRPC });
            const props = {
                resModel: "animal",
                type: "toy_2",
                viewId: 2,
            };
            await mount(View, target, { env, props });
            assert.containsOnce(target, ".o_toy_view.toy_imp", "jsClass from arch prefered");
        }
    );

    QUnit.skip(
        "rendering with given arch attribute 'js_class' and given jsClass",
        async function (assert) {
            class ToyView2 extends Component {}
            ToyView2.template = xml`<div class="o_toy_view_2"/>`;
            ToyView2.type = "toy";
            viewRegistry.add("toy_2", ToyView2);

            const mockRPC = () => {
                throw new Error("no RPC expected");
            };
            const env = await makeTestEnv({ serverData, mockRPC });
            const props = {
                resModel: "animal",
                type: "toy_2",
                arch: `<toy js_class="toy_imp"/>`,
                fields: {},
            };
            await mount(View, target, { env, props });
            assert.containsOnce(target, ".o_toy_view.toy_imp", "jsClass from arch prefered");
        }
    );

    ////////////////////////////////////////////////////////////////////////////
    // props validation
    ////////////////////////////////////////////////////////////////////////////

    QUnit.test("'resModel' must be passed as prop", async function (assert) {
        const env = await makeTestEnv({ serverData });
        const props = {};
        try {
            await mount(View, target, { env, props });
        } catch (error) {
            assert.step(error.message);
        }
        assert.verifySteps([`View props should have a "resModel" key`]);
    });

    QUnit.test("'type' must be passed as prop", async function (assert) {
        const env = await makeTestEnv({ serverData });
        const props = { resModel: "animal" };
        try {
            await mount(View, target, { env, props });
        } catch (error) {
            assert.step(error.message);
        }
        assert.verifySteps([`View props should have a "type" key`]);
    });

    QUnit.test("'arch' cannot be passed as prop alone", async function (assert) {
        const env = await makeTestEnv({ serverData });
        const props = { resModel: "animal", type: "toy", arch: "<toy/>" };
        try {
            await mount(View, target, { env, props });
        } catch (error) {
            assert.step(error.message);
        }
        assert.verifySteps([`"arch" and "fields" props must be given together`]);
    });

    QUnit.test("'fields' cannot be passed as prop alone", async function (assert) {
        const env = await makeTestEnv({ serverData });
        const props = { resModel: "animal", type: "toy", fields: {} };
        try {
            await mount(View, target, { env, props });
        } catch (error) {
            assert.step(error.message);
        }
        assert.verifySteps([`"arch" and "fields" props must be given together`]);
    });

    QUnit.test("'searchViewArch' cannot be passed as prop alone", async function (assert) {
        const env = await makeTestEnv({ serverData });
        const props = { resModel: "animal", type: "toy", searchViewArch: "<toy/>" };
        try {
            await mount(View, target, { env, props });
        } catch (error) {
            assert.step(error.message);
        }
        assert.verifySteps([
            `"searchViewArch" and "searchViewFields" props must be given together`,
        ]);
    });

    QUnit.test("'searchViewFields' cannot be passed as prop alone", async function (assert) {
        const env = await makeTestEnv({ serverData });
        const props = { resModel: "animal", type: "toy", searchViewFields: {} };
        try {
            await mount(View, target, { env, props });
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

            class ToyController extends Component {
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
            ToyController.template = xml`<div/>`;

            viewRegistry.add("toy", { type: "toy", Controller: ToyController }, { force: true });

            const env = await makeTestEnv({ serverData });
            const props = {
                resModel: "animal",
                type: "toy",
                domain: [[0, "=", 1]],
                groupBy: ["birthday"],
                context: { key: "val" },
                orderBy: ["bar"],
            };
            await mount(View, target, { env, props });
        }
    );

    QUnit.test("non empty prop 'noContentHelp'", async function (assert) {
        assert.expect(1);

        class ToyController extends Component {
            setup() {
                assert.strictEqual(this.props.info.noContentHelp, "<div>Help</div>");
            }
        }
        ToyController.template = xml`<div/>`;
        viewRegistry.add("toy", { type: "toy", Controller: ToyController }, { force: true });

        const env = await makeTestEnv({ serverData });
        const props = {
            resModel: "animal",
            type: "toy",
            noContentHelp: "<div>Help</div>",
        };
        await mount(View, target, { env, props });
    });

    QUnit.test("useSampleModel false by default", async function (assert) {
        assert.expect(1);

        class ToyController extends Component {
            setup() {
                assert.strictEqual(this.props.useSampleModel, false);
            }
        }
        ToyController.template = xml`<div/>`;
        viewRegistry.add("toy", { type: "toy", Controller: ToyController }, { force: true });

        const env = await makeTestEnv({ serverData });
        const props = { resModel: "animal", type: "toy" };
        await mount(View, target, { env, props });
    });

    QUnit.test("sample='1' on arch", async function (assert) {
        assert.expect(1);

        class ToyController extends Component {
            setup() {
                assert.strictEqual(this.props.useSampleModel, true);
            }
        }
        ToyController.template = xml`<div/>`;
        viewRegistry.add("toy", { type: "toy", Controller: ToyController }, { force: true });

        const env = await makeTestEnv({ serverData });
        const props = {
            resModel: "animal",
            type: "toy",
            arch: `<toy sample="1"/>`,
            fields: {},
        };
        await mount(View, target, { env, props });
    });

    QUnit.test("sample='0' on arch and useSampleModel=true", async function (assert) {
        assert.expect(1);

        class ToyController extends Component {
            setup() {
                assert.strictEqual(this.props.useSampleModel, true);
            }
        }
        ToyController.template = xml`<div/>`;
        viewRegistry.add("toy", { type: "toy", Controller: ToyController }, { force: true });

        const env = await makeTestEnv({ serverData });
        const props = {
            resModel: "animal",
            type: "toy",
            useSampleModel: true,
            arch: `<toy sample="0"/>`,
            fields: {},
        };
        await mount(View, target, { env, props });
    });

    QUnit.test("sample='1' on arch and useSampleModel=false", async function (assert) {
        assert.expect(1);

        class ToyController extends Component {
            setup() {
                assert.strictEqual(this.props.useSampleModel, false);
            }
        }
        ToyController.template = xml`<div/>`;
        viewRegistry.add("toy", { type: "toy", Controller: ToyController }, { force: true });

        const env = await makeTestEnv({ serverData });
        const props = {
            resModel: "animal",
            type: "toy",
            useSampleModel: false,
            arch: `<toy sample="1"/>`,
            fields: {},
        };
        await mount(View, target, { env, props });
    });

    QUnit.test("useSampleModel=true", async function (assert) {
        assert.expect(1);

        class ToyController extends Component {
            setup() {
                assert.strictEqual(this.props.useSampleModel, true);
            }
        }
        ToyController.template = xml`<div/>`;
        viewRegistry.add("toy", { type: "toy", Controller: ToyController }, { force: true });

        const env = await makeTestEnv({ serverData });
        const props = { resModel: "animal", type: "toy", useSampleModel: true };
        await mount(View, target, { env, props });
    });

    QUnit.test("rendering with given prop", async function (assert) {
        assert.expect(1);

        class ToyController extends Component {
            setup() {
                assert.strictEqual(this.props.specificProp, "specificProp");
            }
        }
        ToyController.template = xml`<div/>`;
        viewRegistry.add("toy", { type: "toy", Controller: ToyController }, { force: true });

        const env = await makeTestEnv({ serverData });
        const props = { resModel: "animal", type: "toy", specificProp: "specificProp" };
        await mount(View, target, { env, props });
    });

    QUnit.test(
        "search query props are passed as props to concrete view (specific search arch)",
        async function (assert) {
            assert.expect(4);

            class ToyController extends Component {
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
            ToyController.template = xml`<div/>`;
            viewRegistry.add("toy", { type: "toy", Controller: ToyController }, { force: true });

            const env = await makeTestEnv({ serverData });
            const props = {
                type: "toy",
                resModel: "animal",
                searchViewId: 1,
                domain: [[0, "=", 1]],
                groupBy: ["birthday"],
                context: { search_default_filter: 1, search_default_group_by: 1 },
                orderBy: ["bar"],
            };
            await mount(View, target, { env, props });
        }
    );

    ////////////////////////////////////////////////////////////////////////////
    // update props
    ////////////////////////////////////////////////////////////////////////////

    QUnit.test("react to prop 'domain' changes", async function (assert) {
        assert.expect(2);

        class ToyController extends Component {
            setup() {
                onWillStart(() => {
                    assert.deepEqual(this.props.domain, [["type", "=", "carnivorous"]]);
                });
                onWillUpdateProps((nextProps) => {
                    assert.deepEqual(nextProps.domain, [["type", "=", "herbivorous"]]);
                });
            }
        }
        ToyController.template = xml`<div/>`;
        viewRegistry.add("toy", { type: "toy", Controller: ToyController }, { force: true });

        const env = await makeTestEnv({ serverData });

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

        const parent = await mount(Parent, target, { env });

        parent.state.domain = [["type", "=", "herbivorous"]];

        await nextTick();
    });
});
