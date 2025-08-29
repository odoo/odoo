import { Component, useState, xml } from "@odoo/owl";
import { beforeEach, expect, test } from "@odoo/hoot";
import { click, queryAllTexts, edit, press, animationFrame, runAllTimers } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { mountWithCleanup, defineParams } from "@web/../tests/web_test_helpers";
import { TimePicker } from "@web/core/time_picker/time_picker";
import { Dropdown } from "@web/core/dropdown/dropdown";

/**
 * @param {any} value
 */
const pad2 = (value) => String(value).padStart(2, "0");

/**
 * @template {any} [T=number]
 * @param {number} length
 * @param {(index: number) => T} mapping
 */
const range = (length, mapping = (n) => n) => [...Array(length)].map((_, i) => mapping(i));

const getTimeOptions = (rounding = 15) => {
    const _hours = range(24, String);
    const _minutes = range(60, (i) => i)
        .filter((i) => i % rounding === 0)
        .map((i) => pad2(i));
    return _hours.flatMap((h) => _minutes.map((m) => `${h}:${m}`));
};

defineParams({
    lang_parameters: {
        time_format: "%H:%M:%S",
    },
});

beforeEach(() => {
    mockDate("2023-04-25T12:45:01");
});

test("default params, click on suggestion to select time", async () => {
    await mountWithCleanup(TimePicker);

    expect(".o_time_picker").toHaveCount(1);
    expect("input.o_time_picker_input").toHaveValue("0:00");

    await click(".o_time_picker_input");
    await animationFrame();

    expect(".o-dropdown--menu.o_time_picker_dropdown").toHaveCount(1);
    expect(queryAllTexts(".o_time_picker_option")).toEqual(getTimeOptions());

    await click(".o_time_picker_option:contains(12:15)");
    await animationFrame();

    expect("input.o_time_picker_input").toHaveValue("12:15");
});

test("when opening, select the suggestion equals to the props value", async () => {
    await mountWithCleanup(TimePicker, {
        props: {
            value: "12:30",
        },
    });

    expect("input.o_time_picker_input").toHaveValue("12:30");

    await click(".o_time_picker_input");
    await animationFrame();

    expect(".o-dropdown--menu.o_time_picker_dropdown").toHaveCount(1);
    expect(queryAllTexts(".o_time_picker_option")).toEqual(getTimeOptions());
    expect(".o_time_picker_option:contains(12:30)").toHaveClass("focus");
});

test("onChange only triggers if the value has changed", async () => {
    await mountWithCleanup(TimePicker, {
        props: {
            value: "12:15",
            onChange: (value) => expect.step(`${value.hour}:${value.minute}`),
        },
    });

    expect("input.o_time_picker_input").toHaveValue("12:15");

    await click(".o_time_picker_input");
    await animationFrame();
    await click(".o_time_picker_option:contains(12:15)");
    await animationFrame();

    expect(".o-dropdown--menu.o_time_picker_dropdown").toHaveCount(0);
    expect("input.o_time_picker_input").toHaveValue("12:15");
    expect.verifySteps([]);

    await click(".o_time_picker_input");
    await animationFrame();
    await click(".o_time_picker_option:contains(12:30)");
    await animationFrame();

    expect(".o-dropdown--menu.o_time_picker_dropdown").toHaveCount(0);
    expect("input.o_time_picker_input").toHaveValue("12:30");
    expect.verifySteps(["12:30"]);
});

test("seconds only shown and usable when 'showSeconds' is true", async () => {
    await mountWithCleanup(TimePicker, {
        props: {
            showSeconds: true,
            onChange: (value) => expect.step(`${value.hour}:${value.minute}:${value.second}`),
        },
    });

    expect("input.o_time_picker_input").toHaveValue("0:00:00");

    await click(".o_time_picker_input");
    await animationFrame();

    await click(".o_time_picker_option:contains(12:15)");
    await animationFrame();

    expect("input.o_time_picker_input").toHaveValue("12:15:00");
    expect.verifySteps(["12:15:0"]);

    await click(".o_time_picker_input");
    await edit("15:25:33", { confirm: "enter" });
    await animationFrame();
    expect("input.o_time_picker_input").toHaveValue("15:25:33");
    expect.verifySteps(["15:25:33"]);
});

test("handle 12h (am/pm) time format", async () => {
    defineParams({
        lang_parameters: {
            time_format: "hh:mm:ss a",
        },
    });

    await mountWithCleanup(TimePicker, {
        props: {
            onChange: (value) => expect.step(`${value.hour}:${value.minute}`),
        },
    });

    expect("input.o_time_picker_input").toHaveValue("12:00am");

    await click(".o_time_picker_input");
    await animationFrame();

    const M = range(60, (i) => i)
        .filter((i) => i % 15 === 0)
        .map((i) => pad2(i));
    const H = [12, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
    const options = [];
    ["am", "pm"].forEach((a) => H.forEach((h) => M.forEach((m) => options.push(`${h}:${m}${a}`))));
    expect(queryAllTexts(".o_time_picker_dropdown .o_time_picker_option")).toEqual(options);

    await edit("4:15pm", { confirm: "enter" });
    await animationFrame();
    expect("input.o_time_picker_input").toHaveValue("4:15pm");
    // actual data is always in 24h format
    expect.verifySteps(["16:15"]);

    await edit("8:30", { confirm: "enter" });
    await animationFrame();
    // default to am when no meridiem is provided
    expect("input.o_time_picker_input").toHaveValue("8:30am");
    expect.verifySteps(["8:30"]);
});

test.tags("desktop");
test("validity updated on input and cannot apply non-valid time strings", async () => {
    await mountWithCleanup(TimePicker, {
        props: {
            onChange: () => expect.step("change"),
        },
    });

    await click(".o_time_picker_input");
    await animationFrame();

    await edit("gg ez", { confirm: false });
    await animationFrame();
    expect("input.o_time_picker_input").toHaveClass("o_invalid");

    await press("enter");
    await animationFrame();
    expect.verifySteps([]);

    await edit("12:30", { confirm: false });
    await animationFrame();
    expect("input.o_time_picker_input").not.toHaveClass("o_invalid");
    expect.verifySteps([]);

    await press("enter");
    await animationFrame();
    expect.verifySteps(["change"]);
});

test.tags("desktop");
test("arrow keys navigation, enter selects items, up/down arrow updates the input value", async () => {
    await mountWithCleanup(TimePicker, {
        props: {
            onChange: (value) => expect.step(`${value.hour}:${value.minute}`),
        },
    });

    await click(".o_time_picker_input");
    await animationFrame();
    expect("input.o_time_picker_input").toHaveValue("0:00");

    await press("arrowdown");
    await animationFrame();
    expect("input.o_time_picker_input").toHaveValue("0:15");

    await press("arrowup");
    await press("arrowup");
    await animationFrame();
    expect("input.o_time_picker_input").toHaveValue("23:45");

    await press("enter");
    await animationFrame();
    expect.verifySteps(["23:45"]);
});

test.tags("desktop");
test("if typing after navigating, enter validates input value", async () => {
    await mountWithCleanup(TimePicker, {
        props: {
            onChange: (value) => expect.step(`${value.hour}:${value.minute}`),
        },
    });

    await click(".o_time_picker_input");
    await animationFrame();

    await press("arrowdown");
    await animationFrame();
    expect("input.o_time_picker_input").toHaveValue("0:15");

    await press("enter");
    await animationFrame();
    // Enter selects the navigated item
    expect.verifySteps(["0:15"]);

    await click(".o_time_picker_input");
    await animationFrame();

    await press("arrowdown");
    await press("arrowdown");
    await animationFrame();
    expect("input.o_time_picker_input").toHaveValue("0:45");

    await edit("12:5", { confirm: false });
    await press("enter");
    await animationFrame();
    // Enter validates the edited input
    expect.verifySteps(["12:50"]);
});

test("typing a value that is in the suggestions will focus it in the dropdown", async () => {
    await mountWithCleanup(TimePicker);

    await click(".o_time_picker_input");
    await animationFrame();
    await runAllTimers();
    expect(".o_time_picker_option.focus").toHaveText("0:00");

    await edit("12:3", { confirm: false });
    await animationFrame();
    expect(".o_time_picker_option.focus").toHaveText("12:30");
    expect(".o_time_picker_option.focus").toBeVisible();
});

test("false, null and undefined are accepted values", async () => {
    class Parent extends Component {
        static components = { TimePicker };
        static props = {};
        static template = xml`<TimePicker value="state.value"/>`;

        setup() {
            this.state = useState({
                value: null,
            });
        }
    }

    const comp = await mountWithCleanup(Parent);
    expect(".o_time_picker_input").toHaveValue("");

    comp.state.value = false;
    await runAllTimers();
    expect(".o_time_picker_input").toHaveValue("");

    comp.state.value = undefined;
    await runAllTimers();
    expect(".o_time_picker_input").toHaveValue("0:00");
});

test("click-out triggers onChange", async () => {
    class Parent extends Component {
        static components = { TimePicker, Dropdown };
        static props = {};
        static template = xml`
            <div>
                <Dropdown>
                    <button class="open">Open</button>
                    <t t-set-slot="content">
                        <TimePicker onChange.bind="onChange"/>
                    </t>
                </Dropdown>
                <button class="outside">Outside</button>
            </div>
        `;

        onChange(value) {
            expect.step(`${value.hour}:${value.minute}`);
        }
    }

    await mountWithCleanup(Parent);

    await click(".open");
    await animationFrame();

    await click(".o_time_picker_input");
    await animationFrame();
    expect(".o_time_picker_option.focus").toHaveText("0:00");

    await edit("12:3", { confirm: false });
    await animationFrame();
    expect.verifySteps([]);

    await click(".outside");
    await animationFrame();
    expect(".o-dropdown--menu.o_time_picker_dropdown").toHaveCount(0);
    expect.verifySteps(["12:30"]);
});

test("changing the props value updates the input", async () => {
    class Parent extends Component {
        static components = { TimePicker };
        static props = {};
        static template = xml`<TimePicker value="state.value" onChange.bind="onChange"/>`;

        setup() {
            this.state = useState({
                value: null,
            });
        }

        onChange(value) {
            expect.step(`${value.hour}:${value.minute}`);
        }
    }

    const comp = await mountWithCleanup(Parent);
    expect(".o_time_picker_input").toHaveValue("");

    // Set value from props
    comp.state.value = "12:00";
    await runAllTimers();
    expect(".o_time_picker_input").toHaveValue("12:00");
    expect.verifySteps([]);

    // Set value by clicking
    await click(".o_time_picker_input");
    await animationFrame();
    await click(`.o_time_picker_option:contains("11:30")`);
    await animationFrame();
    await runAllTimers();
    expect.verifySteps(["11:30"]);

    // Set falsy value from props
    comp.state.value = false;
    await runAllTimers();
    expect(".o_time_picker_input").toHaveValue("");
    expect.verifySteps([]);
});

test("ensure placeholder is customizable", async () => {
    class Parent extends Component {
        static components = { TimePicker };
        static props = {};
        static template = xml`<TimePicker placeholder="state.placeholder"/>`;

        setup() {
            this.state = useState({ placeholder: undefined });
        }
    }

    const comp = await mountWithCleanup(Parent);
    await animationFrame();
    expect(".o_time_picker_input").toHaveAttribute("placeholder", "hh:mm");

    comp.state.placeholder = "your time";
    await animationFrame();
    expect(".o_time_picker_input").toHaveAttribute("placeholder", "your time");
});

test("add a custom class", async () => {
    class Parent extends Component {
        static components = { TimePicker };
        static props = {};
        static template = xml`<TimePicker cssClass="'o_custom_class'"/>`;
    }

    await mountWithCleanup(Parent);
    expect(".o_time_picker").toHaveClass("o_custom_class");
});

test("add a custom input class", async () => {
    class Parent extends Component {
        static components = { TimePicker };
        static props = {};
        static template = xml`<TimePicker inputCssClass="'o_custom_class'"/>`;
    }

    await mountWithCleanup(Parent);
    expect(".o_time_picker_input").toHaveClass("o_custom_class");
});
