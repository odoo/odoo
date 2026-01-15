import { expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { ViewScaleSelector } from "@web/views/view_components/view_scale_selector";

test("basic ViewScaleSelector component usage", async () => {
    class Parent extends Component {
        static components = { ViewScaleSelector };
        static template = xml`<ViewScaleSelector t-props="compProps" />`;
        static props = ["*"];
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
                    expect.step(scale);
                },
                toggleWeekendVisibility: () => {
                    expect.step("toggleWeekendVisibility");
                },
                currentScale: this.state.scale,
            };
        }
    }

    await mountWithCleanup(Parent);
    expect(".o_view_scale_selector").toHaveCount(1);
    expect.verifySteps([]);
    expect(".o_view_scale_selector").toHaveText("Weekly");
    expect(".scale_button_selection").toHaveAttribute("data-hotkey", "v");
    await click(".scale_button_selection");
    await animationFrame();
    expect(".o-dropdown--menu").toHaveCount(1);
    expect(".o-dropdown--menu .active:first").toHaveText("Weekly", {
        message: "the active option is selected",
    });
    expect(".o-dropdown--menu span:nth-child(2)").toHaveAttribute("data-hotkey", "o", {
        message: "'week' scale has the right hotkey",
    });
    await click(".o_scale_button_day");
    await animationFrame();
    expect.verifySteps(["day"]);
    expect(".o_view_scale_selector").toHaveText("Daily");
    await click(".scale_button_selection");
    expect(".dropdown-item:last:interactive").not.toHaveCount();
    await contains(".dropdown-item:contains(Yearly)").click();
    await click(".scale_button_selection");
    await contains(".dropdown-item:last").click();
    expect.verifySteps(["year", "toggleWeekendVisibility"]);
});

test("ViewScaleSelector with only one scale available", async () => {
    class Parent extends Component {
        static components = { ViewScaleSelector };
        static template = xml`<ViewScaleSelector t-props="compProps" />`;
        static props = ["*"];
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

    await mountWithCleanup(Parent);
    expect(".o_view_scale_selector").toHaveCount(0);
});

test("ViewScaleSelector show weekends button is disabled when scale is day", async () => {
    class Parent extends Component {
        static components = { ViewScaleSelector };
        static template = xml`<ViewScaleSelector t-props="compProps"/>`;
        static props = ["*"];
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
                    week: {
                        description: "Weekly",
                        hotkey: "o",
                    },
                    year: {
                        description: "Yearly",
                    },
                },
                setScale: (key) => (this.state.scale = key),
                isWeekendVisible: false,
                toggleWeekendVisibility: () => {},
                currentScale: this.state.scale,
            };
        }
    }

    await mountWithCleanup(Parent);
    expect(".o_view_scale_selector").toHaveCount(1);
    await click(".scale_button_selection");
    await animationFrame();
    expect(".o_show_weekends").toHaveClass("disabled");
    await click(".dropdown-item:nth-child(2)");
    await animationFrame();
    await click(".scale_button_selection");
    await animationFrame();
    expect(".o_show_weekends").not.toHaveClass("disabled");
});
