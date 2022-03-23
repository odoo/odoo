/** @odoo-module */
import { makeTestEnv } from "../helpers/mock_env";
import { viewService } from "@web/views/view_service";
import { registry } from "@web/core/registry";
import { makeMockServer } from "../helpers/mock_server";
import { ormService } from "@web/core/orm_service";

QUnit.module("View service", (hooks) => {
    let serverData;

    hooks.beforeEach(() => {
        const views = {
            "take.five,99,list": `<list><field name="display_name" /><list>`,
        };

        const models = {
            "take.five": {
                fields: {},
                records: [],
            },
        };

        const fakeUiService = {
            start(env) {
                Object.defineProperty(env, "isSmall", {
                    get() {
                        return false;
                    },
                });
            },
        };
        serverData = { models, views };
        registry
            .category("services")
            .add("views", viewService)
            .add("orm", ormService)
            .add("ui", fakeUiService);
    });

    QUnit.test("stores calls in cache in success", async (assert) => {
        assert.expect(2);

        const mockRPC = (route, args) => {
            if (route.includes("get_views")) {
                assert.step("get_views");
            }
        };

        makeMockServer(serverData, mockRPC);
        const env = await makeTestEnv();

        await env.services.views.loadViews(
            {
                resModel: "take.five",
                views: [[99, "list"]],
            },
            {}
        );
        await env.services.views.loadViews(
            {
                resModel: "take.five",
                views: [[99, "list"]],
            },
            {}
        );

        assert.verifySteps(["get_views"]);
    });

    QUnit.test("stores calls in cache when failed", async (assert) => {
        assert.expect(5);

        const mockRPC = (route, args) => {
            if (route.includes("get_views")) {
                assert.step("get_views");
                return Promise.reject("my little error");
            }
        };

        makeMockServer(serverData, mockRPC);
        const env = await makeTestEnv();

        try {
            await env.services.views.loadViews(
                {
                    resModel: "take.five",
                    views: [[99, "list"]],
                },
                {}
            );
        } catch (error) {
            assert.strictEqual(error, "my little error");
        }

        try {
            await env.services.views.loadViews(
                {
                    resModel: "take.five",
                    views: [[99, "list"]],
                },
                {}
            );
        } catch (error) {
            assert.strictEqual(error, "my little error");
        }

        assert.verifySteps(["get_views", "get_views"]);
    });
});
