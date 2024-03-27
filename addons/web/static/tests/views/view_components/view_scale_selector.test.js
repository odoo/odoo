import { expect, test } from "@odoo/hoot";
import { click, queryAll } from "@odoo/hoot-dom";
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
    expect([]).toVerifySteps();
    expect(".o_view_scale_selector").toHaveText("Weekly");
    expect(".scale_button_selection").toHaveAttribute("data-hotkey", "v");
    click(".scale_button_selection");
    await animationFrame();
    expect(".o-dropdown--menu").toHaveCount(1);
    expect(queryAll(".o-dropdown--menu .active")[0], {
        message: "the active option is selected",
    }).toHaveText("Weekly");
    expect(".o-dropdown--menu span:nth-child(2)", {
        message: "'week' scale has the right hotkey",
    }).toHaveAttribute("data-hotkey", "o");
    click(".o_scale_button_day");
    await animationFrame();
    expect(["day"]).toVerifySteps();
    expect(".o_view_scale_selector").toHaveText("Daily");
    click(".scale_button_selection");
    await contains(".dropdown-item:last-child").click();
    expect(["toggleWeekendVisibility"]).toVerifySteps();
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
    click(".scale_button_selection");
    await animationFrame();
    expect(".o_show_weekends").toHaveClass("disabled");
    click(".dropdown-item:nth-child(2)");
    await animationFrame();
    click(".scale_button_selection");
    await animationFrame();
    expect(".o_show_weekends").not.toHaveClass("disabled");
});
