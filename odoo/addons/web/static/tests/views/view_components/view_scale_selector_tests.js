/** @odoo-module **/

import { Component, useState, xml } from "@odoo/owl";
import { ViewScaleSelector } from "@web/views/view_components/view_scale_selector";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { click, getFixture, mount } from "@web/../tests/helpers/utils";
import { registry } from "@web/core/registry";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { uiService } from "@web/core/ui/ui_service";

const serviceRegistry = registry.category("services");
let target;

QUnit.module("ViewComponents", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
        serviceRegistry.add("ui", uiService);
        serviceRegistry.add("hotkey", hotkeyService);
    });

    QUnit.module("ViewScaleSelector");

    QUnit.test("basic ViewScaleSelector component usage", async (assert) => {
        const env = await makeTestEnv();

        class Parent extends Component {
            static components = { ViewScaleSelector };
            static template = xml`<ViewScaleSelector t-props="compProps" />`;
            setup() {
                this.state = useState({
                    scale: "week",
                });
            }
            get compProps() {
                return {
                    scales: {
                        day: {
                            description: "Daily",
                        },
                        week: {
                            description: "Weekly",
                            hotkey: "o",
                        },
                        year: {
                            description: "Yearly",
                        },
                    },
                    isWeekendVisible: true,
                    setScale: (scale) => {
                        this.state.scale = scale;
                        assert.step(scale);
                    },
                    toggleWeekendVisibility: () => {
                        assert.step("toggleWeekendVisibility");
                    },
                    currentScale: this.state.scale,
                };
            }
        }

        await mount(Parent, target, { env });
        assert.containsOnce(target, ".o_view_scale_selector");
        assert.verifySteps([]);
        assert.strictEqual(
            target.querySelector(".o_view_scale_selector").textContent,
            "Weekly",
            "toggler displays the right text"
        );
        assert.strictEqual(
            target.querySelector(".scale_button_selection").dataset.hotkey,
            "v",
            "toggler has the right hotkey"
        );

        await click(target, ".scale_button_selection");
        assert.containsOnce(target, ".o_view_scale_selector .dropdown-menu", "a dropdown appeared");
        assert.strictEqual(
            target.querySelector(".o_view_scale_selector .dropdown-menu .active").textContent,
            "Weekly",
            "the active option is selected"
        );
        assert.strictEqual(
            target.querySelector(".o_view_scale_selector .dropdown-menu span:nth-child(2)").dataset
                .hotkey,
            "o",
            "'week' scale has the right hotkey"
        );

        await click(target, ".o_scale_button_day");
        assert.verifySteps(["day"]);
        assert.strictEqual(
            target.querySelector(".o_view_scale_selector").textContent,
            "Daily",
            "the right text is displayed on the toggler"
        );

        await click(target, ".scale_button_selection");
        await click(target, ".dropdown-item:last-child");
        assert.verifySteps(["toggleWeekendVisibility"]);
    });

    QUnit.test("ViewScaleSelector with only one scale available", async (assert) => {
        const env = await makeTestEnv();

        class Parent extends Component {
            static components = { ViewScaleSelector };
            static template = xml`<ViewScaleSelector t-props="compProps" />`;
            setup() {
                this.state = useState({
                    scale: "day",
                });
            }
            get compProps() {
                return {
                    scales: {
                        day: {
                            description: "Daily",
                        },
                    },
                    setScale: () => {},
                    isWeekendVisible: false,
                    toggleWeekendVisibility: () => {},
                    currentScale: this.state.scale,
                };
            }
        }

        await mount(Parent, target, { env });
        assert.containsNone(
            target,
            ".o_view_scale_selector",
            "toggler is not present as no other option is available"
        );
    });
});
