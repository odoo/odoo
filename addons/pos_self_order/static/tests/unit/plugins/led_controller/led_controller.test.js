import { describe, expect, test, mockFetch, advanceTime } from "@odoo/hoot";
import {
    hexToRgb,
    compareVersion,
    ODOO_COLOR,
    SUCCESS_COLOR,
    ERROR_COLOR,
    ANIMATION_DURATION_MS,
} from "@pos_self_order/app/plugins/led_controller/utils";
import {
    LedControllerPlugin,
    DefaultStrategy,
} from "@pos_self_order/app/plugins/led_controller/led_controller_plugin";
import { BoxaPosStrategy } from "@pos_self_order/app/plugins/led_controller/boxapos_strategy";

describe("LedController", () => {
    describe("Utilities", () => {
        test("hexToRgb converts correctly", () => {
            expect(hexToRgb("#FF0000")).toBe("255,0,0");
            expect(hexToRgb("00FF00")).toBe("0,255,0");
            expect(hexToRgb("#00F")).toBe("0,0,255");
        });

        test("hexToRgb handles invalid formats correctly", () => {
            expect(hexToRgb("XYZ")).toBe(false);
            expect(hexToRgb("")).toBe(false);
            expect(hexToRgb("#12")).toBe(false);
        });

        test("compareVersion handles versions correctly", () => {
            expect(compareVersion("260.812.0", "260.812.1")).toBeGreaterThan(0);
            expect(compareVersion("260.812.0", "260.813.0")).toBeGreaterThan(0);
            expect(compareVersion("260.812.0", "261.812.0")).toBeGreaterThan(0);
            expect(compareVersion("260.812.1", "260.813.0")).toBeGreaterThan(0);
            expect(compareVersion("260.812.0", "261.810.0")).toBeGreaterThan(0);

            expect(compareVersion("260.812.0", "250.0.0")).toBeLessThan(0);
            expect(compareVersion("260.812.0", "259.813.0")).toBeLessThan(0);
            expect(compareVersion("260.812.0", "259.812.1")).toBeLessThan(0);

            expect(compareVersion("260.812.0", "260.812.0")).toBe(0);
        });

        test("compareVersion handles invalid versions correctly", () => {
            expect(compareVersion("260.812.0", "beta-version")).toBe(false);
            expect(compareVersion("260.812.0", "")).toBe(false);
            expect(compareVersion("260.812.0", null)).toBe(false);
            expect(compareVersion("260.812.0", undefined)).toBe(false);
            expect(compareVersion("beta-version", "260.812.0")).toBe(false);
            expect(compareVersion("", "260.812.0")).toBe(false);
            expect(compareVersion(null, "260.812.0")).toBe(false);
            expect(compareVersion(undefined, "260.812.0")).toBe(false);
        });
    });

    describe("Plugin", () => {
        function setupPlugin(idleColor = "") {
            const plugin = new LedControllerPlugin();
            plugin.idleColor = ODOO_COLOR;
            plugin.strategy = new DefaultStrategy();

            plugin.lockTimer = null;
            plugin.isLocked = false;
            plugin.pendingColor = null;

            return plugin;
        }

        test("switch to defaultStrategy when action fail", async () => {
            const plugin = setupPlugin();
            plugin.strategy = "Other strategy";

            const failedAction = async () => {
                expect.step("action_failed");
                return false;
            };

            await plugin.playAnimation(failedAction);

            expect.verifySteps(["action_failed"]);
            expect(plugin.strategy).toBeInstanceOf(DefaultStrategy);
        });

        test("switch to defaultStrategy when action throw a error", async () => {
            const plugin = setupPlugin();
            plugin.strategy = "Other strategy";

            const errorAction = async () => {
                expect.step("action_throw_error");
                throw Error();
            };

            await plugin.playAnimation(errorAction);

            expect.verifySteps(["action_throw_error"]);
            expect(plugin.strategy).toBeInstanceOf(DefaultStrategy);
        });

        test("FIFO for animation", async () => {
            const plugin = setupPlugin();
            const firstAction = async () => {
                expect.step("first_action");
                return true;
            };
            const secondAction = async () => {
                expect.step("second_action");
                return true;
            };

            await plugin.playAnimation(firstAction);
            expect.verifySteps(["first_action"]);

            await plugin.playAnimation(secondAction);
            expect.verifySteps(["second_action"]);
        });

        test("pendingColor can be changed during animation", async () => {
            const plugin = setupPlugin();
            plugin.setIdleState = async (color) => {
                expect.step(`Color_${color}`);
            };

            const validAction = async () => true;

            const animPromise = await plugin.playAnimation(
                validAction,
                SUCCESS_COLOR,
                ANIMATION_DURATION_MS
            );

            expect(plugin.pendingColor).toBe(SUCCESS_COLOR);
            plugin.pendingColor = ERROR_COLOR;

            await animPromise;
            await advanceTime(ANIMATION_DURATION_MS);

            expect.verifySteps([`Color_${ERROR_COLOR}`]);
        });

        test("setIdleState is ignored when an animation is played", async () => {
            const plugin = setupPlugin();

            plugin.strategy = {
                setSuccessState: async () => expect.step("strategy_success"),
                setIdleState: async (color) => expect.step(`strategy_idle_${color}`),
            };

            const animPromise = plugin.setSuccessState();
            expect.verifySteps(["strategy_success"]);
            expect(plugin.isLocked).toBe(true);

            await plugin.setIdleState("0,0,255");
            expect.verifySteps([]);
            expect(plugin.pendingColor).toBe("0,0,255");

            await animPromise;
            await advanceTime(ANIMATION_DURATION_MS);

            expect(plugin.isLocked).toBe(false);
            expect(plugin.pendingColor).toBe(null);
            expect.verifySteps(["strategy_idle_0,0,255"]);
        });

        test("setErrorState plays animation and unlocks after duration", async () => {
            const plugin = new LedControllerPlugin();
            plugin.idleColor = "255,255,255";

            plugin.strategy = {
                setErrorState: async () => expect.step("strategy_error"),
                setIdleState: async () => expect.step("strategy_idle"),
            };

            const promise = plugin.setErrorState();
            expect.verifySteps(["strategy_error"]);
            expect(plugin.isLocked).toBe(true);

            await promise;
            await advanceTime(ANIMATION_DURATION_MS);

            expect(plugin.isLocked).toBe(false);
            expect.verifySteps(["strategy_idle"]);
        });

        test("playAnimation handles strategy rejection without crashing", async () => {
            const plugin = new LedControllerPlugin();
            plugin.strategy = {
                setSuccessState: async () => {
                    throw new Error("Hardware failure");
                },
                setIdleState: async () => {},
            };

            await expect(plugin.setSuccessState()).resolves.toBe(undefined);

            expect(plugin.isLocked).toBe(true);
            await advanceTime(ANIMATION_DURATION_MS);
            expect(plugin.isLocked).toBe(false);
        });
    });

    describe("BoxaPosStrategy", () => {
        test("detect() return false if old version", async () => {
            mockFetch((url, options) => {
                if (url.includes("/status")) {
                    return new Response(
                        JSON.stringify({
                            name: "Kiosk",
                            platform: "android",
                            version: "250.0.0",
                            capabilities: ["setColor", "setPreset", "getPresets", "applyPreset"],
                            ledController: { connected: true },
                        })
                    );
                }
            });

            const result = await BoxaPosStrategy.detect();

            expect(result).toBe(false);
        });

        test("detect() returns strategy instance if compatible", async () => {
            mockFetch((url, options) => {
                if (url.includes("/status")) {
                    return new Response(
                        JSON.stringify({
                            name: "Kiosk",
                            platform: "android",
                            version: "260.812.1",
                            capabilities: ["setColor", "setPreset", "getPresets", "applyPreset"],
                            ledController: { connected: true },
                        })
                    );
                }
            });

            const result = await BoxaPosStrategy.detect();

            expect(result).toBeInstanceOf(BoxaPosStrategy);
        });

        test("detect() returns false if an error is thrown", async () => {
            mockFetch((url, options) => {
                throw Error("Network Error");
            });

            const result = await BoxaPosStrategy.detect();

            expect(result).toBe(false);
        });

        test("sendCommand handles HTTP errors gracefully without rejecting", async () => {
            mockFetch(() => new Response("Internal Server Error", { status: 500 }));

            const strategy = new BoxaPosStrategy();

            const result = await strategy.sendCommand("testAction");
            expect(result).toBe(false);
        });

        test("applyPreset and setIdleState format the POST requests correctly", async () => {
            let receivedBody = {};
            mockFetch((url, options) => {
                if (options && options.body) {
                    receivedBody = JSON.parse(options.body);
                }
                return new Response(JSON.stringify({ success: true }));
            });

            const strategy = new BoxaPosStrategy();

            await strategy.applyPreset(2);
            expect(receivedBody).toEqual({ action: "applyPreset", value: 2 });

            await strategy.setIdleState("255,0,0");
            expect(receivedBody).toEqual({ action: "setColor", value: "255,0,0,255" });
        });
    });
});
