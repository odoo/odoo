import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { PosKanbanRenderer } from "@point_of_sale/backend/pos_kanban_view/pos_kanban_view";
import {
    contains,
    defineModels,
    fields,
    MockServer,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { user } from "@web/core/user";

for (const preset of ["desktop", "mobile"]) {
    describe(preset, () => {
        describe.current.tags(preset);

        class PosConfig extends models.Model {
            _name = "pos.config";
            name = fields.Char();
            _records = [];
        }
        defineModels([PosConfig]);

        async function mountKanban({ chart = true, manager = true } = {}) {
            patchWithCleanup(user, { hasGroup: async () => manager });
            onRpc("pos.config", "get_pos_kanban_view_state", () => ({
                has_pos_config: false,
                has_chart_template: chart,
                is_restaurant_installed: true,
                is_main_company: true,
            }));
            return mountView({
                type: "kanban",
                resModel: "pos.config",
                arch: '<kanban js_class="pos_config_kanban_view"><templates><t t-name="card"><field name="name"/></t></templates></kanban>',
            });
        }

        test("scenario controls are disabled without a chart of accounts", async () => {
            await mountKanban({ chart: false });
            expect("button.pos-scenario-card:disabled").toHaveCount(6);
        });

        test("one scenario runs while pending and the new configuration replaces the cards", async () => {
            const loaded = new Deferred();
            let calls = 0;
            onRpc(
                "pos.config",
                "load_onboarding_clothes_scenario",
                async ({ args }) => {
                    expect(args).toEqual([false]);
                    calls++;
                    await loaded;
                    MockServer.env["pos.config"].create({ name: "New shop" });
                    return 1;
                },
            );
            await mountKanban();
            await contains(".pos-scenario-card:first").click();
            expect("button.pos-scenario-card:disabled").toHaveCount(6);
            expect(calls).toBe(1);
            loaded.resolve();
            await animationFrame();
            await animationFrame();
            expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveText("New shop");
            expect(".pos-scenario-card").toHaveCount(0);
        });

        test("denied onboarding does not clear the current search", async () => {
            patchWithCleanup(user, { hasGroup: async () => false });
            let cleared = 0;
            let called = false;
            const renderer = {
                dialog: { add: () => expect.step("denied") },
                env: {
                    searchModel: {
                        clearQuery: async () => {
                            cleared++;
                        },
                    },
                },
            };
            await PosKanbanRenderer.prototype.callWithViewUpdate.call(
                renderer,
                async () => {
                    called = true;
                },
            );
            expect(called).toBe(false);
            expect(cleared).toBe(0);
            expect.verifySteps(["denied"]);
        });

        test("scenario completion awaits the search-model notification", async () => {
            patchWithCleanup(user, { hasGroup: async () => true });
            const refreshed = new Deferred();
            let complete = false;
            const renderer = {
                posState: {},
                orm: { call: async () => ({ has_pos_config: true }) },
                env: { searchModel: { clearQuery: () => refreshed } },
            };
            const pending = PosKanbanRenderer.prototype.callWithViewUpdate
                .call(renderer, async () => 42)
                .then((result) => {
                    complete = true;
                    expect(result).toBe(42);
                });
            await animationFrame();
            expect(complete).toBe(false);
            refreshed.resolve();
            await pending;
            expect(renderer.posState.has_pos_config).toBe(true);
        });

        for (const failure of ["scenario", "state", "search"]) {
            test(`onboarding preserves the ${failure} error when search refresh fails`, async () => {
                patchWithCleanup(user, { hasGroup: async () => true });
                const renderer = {
                    posState: {},
                    orm: {
                        call: async () => {
                            if (failure === "state") {
                                throw new Error("state failed");
                            }
                            return { has_pos_config: true };
                        },
                    },
                    env: {
                        searchModel: {
                            clearQuery: async () => {
                                expect.step("refresh attempted");
                                throw new Error("search failed");
                            },
                        },
                    },
                };
                await expect(
                    PosKanbanRenderer.prototype.callWithViewUpdate.call(
                        renderer,
                        async () => {
                            if (failure === "scenario") {
                                throw new Error("scenario failed");
                            }
                            return 42;
                        },
                    ),
                ).rejects.toThrow(`${failure} failed`);
                expect.verifySteps(["refresh attempted"]);
            });
        }
    });
}
