// @ts-check

import { beforeEach, expect, test } from "@odoo/hoot";
import {
    animationFrame,
    click,
    edit,
    press,
    queryAllTexts,
    queryOne,
    runAllTimers,
} from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { Component, onRendered, useState, xml } from "@odoo/owl";
import {
    defineParams,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { TimePicker } from "@web/components/time_picker/time_picker";

/** @param {any} value */
const pad2 = (value) => String(value).padStart(2, "0");

/**
 * @template T
 * @param {number} length
 * @param {(index: number) => T} mapping
 */
const range = (length, mapping) => [...Array(length)].map((_, i) => mapping(i));

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

test("when opening, the nearest suggestion is highlighted for in-between values", async () => {
    await mountWithCleanup(TimePicker, {
        props: {
            value: "12:29",
            minutesRounding: 1,
        },
    });

    expect("input.o_time_picker_input").toHaveValue("12:29");

    await click(".o_time_picker_input");
    await animationFrame();

    expect(".o_time_picker_option:contains(12:30)").toHaveClass("focus");
});

test("fine minutesRounding keeps a 15-minute suggestion grid but accepts exact values", async () => {
    await mountWithCleanup(TimePicker, {
        props: {
            minutesRounding: 1,
            onChange: (value) => expect.step(`${value.hour}:${value.minute}`),
        },
    });

    await click(".o_time_picker_input");
    await animationFrame();

    expect(queryAllTexts(".o_time_picker_option")).toEqual(getTimeOptions());

    await edit("12:34", { confirm: "enter" });
    await animationFrame();
    expect("input.o_time_picker_input").toHaveValue("12:34");
    expect.verifySteps(["12:34"]);
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
            onChange: (value) =>
                expect.step(`${value.hour}:${value.minute}:${value.second}`),
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
    ["am", "pm"].forEach((a) =>
        H.forEach((h) => M.forEach((m) => options.push(`${h}:${m}${a}`))),
    );
    expect(queryAllTexts(".o_time_picker_dropdown .o_time_picker_option")).toEqual(
        options,
    );

    await edit("4:15pm", { confirm: "enter" });
    await animationFrame();
    expect("input.o_time_picker_input").toHaveValue("4:15pm");
    expect.verifySteps(["16:15"]);

    await edit("8:30", { confirm: "enter" });
    await animationFrame();
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
test("rounding a near-midnight time does not wrap back to the start of the day", async () => {
    await mountWithCleanup(TimePicker, {
        props: {
            onChange: (value) => expect.step(`${value.hour}:${value.minute}`),
        },
    });

    await click(".o_time_picker_input");
    await animationFrame();

    await edit("23:58", { confirm: "enter" });
    await animationFrame();

    expect("input.o_time_picker_input").toHaveValue("23:55");
    expect.verifySteps(["23:55"]);
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
        static template = xml`<TimePicker value="this.state.value"/>`;

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
    await animationFrame();
    expect(".o_time_picker_input").toHaveValue("");

    comp.state.value = undefined;
    await runAllTimers();
    await animationFrame();
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
                        <TimePicker onChange.bind="this.onChange"/>
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
        static template = xml`<TimePicker value="this.state.value" onChange.bind="this.onChange"/>`;

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

    comp.state.value = "12:00";
    await runAllTimers();
    await animationFrame();
    expect(".o_time_picker_input").toHaveValue("12:00");
    expect.verifySteps([]);

    await click(".o_time_picker_input");
    await animationFrame();
    await click(`.o_time_picker_option:contains("11:30")`);
    await animationFrame();
    await runAllTimers();
    expect.verifySteps(["11:30"]);

    comp.state.value = false;
    await runAllTimers();
    await animationFrame();
    expect(".o_time_picker_input").toHaveValue("");
    expect.verifySteps([]);
});

test("ensure placeholder is customizable", async () => {
    class Parent extends Component {
        static components = { TimePicker };
        static props = {};
        static template = xml`<TimePicker placeholder="this.state.placeholder"/>`;

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

test("typing after the dropdown was closed does not select the whole input", async () => {
    await mountWithCleanup(TimePicker, { props: { value: "10:30" } });

    await click(".o_time_picker_input");
    await animationFrame();
    expect(".o_time_picker_dropdown").toHaveCount(1);

    await press("Escape");
    await animationFrame();
    expect(".o_time_picker_dropdown").toHaveCount(0);
    expect(".o_time_picker_input").toBeFocused();

    const input = /** @type {HTMLInputElement} */ (queryOne(".o_time_picker_input"));
    input.setSelectionRange(input.value.length, input.value.length);
    await press("1");
    await animationFrame();
    expect(input.selectionStart).toBe(input.value.length);
    expect(input.selectionEnd).toBe(input.value.length);

    await press("2");
    await animationFrame();
    expect(input).toHaveValue("10:3012");
});

test("focusing or clicking the input still selects it whole", async () => {
    await mountWithCleanup(TimePicker, { props: { value: "10:30" } });
    await click(".o_time_picker_input");
    await animationFrame();

    const input = /** @type {HTMLInputElement} */ (queryOne(".o_time_picker_input"));
    expect(input.selectionStart).toBe(0);
    expect(input.selectionEnd).toBe(input.value.length);
});

test("the input exposes combobox semantics and stays out of the tab order", async () => {
    await mountWithCleanup(TimePicker, { props: { value: "10:30" } });
    const input = queryOne(".o_time_picker_input");
    expect(input).toHaveAttribute("tabindex", "-1");
    expect(input).toHaveAttribute("role", "combobox");
    expect(input).toHaveAttribute("aria-expanded", "false");

    await click(".o_time_picker_input");
    await animationFrame();
    expect(input).toHaveAttribute("aria-expanded", "true");
    expect(input).toHaveAttribute(
        "aria-controls",
        queryOne(".o_time_picker_dropdown").id,
    );
    expect(".o_time_picker_dropdown").toHaveAttribute("role", "listbox");
    expect(".o_time_picker_option:first").toHaveAttribute("role", "option");
});

test("suggestions are rebuilt only when the rounding that shapes them changes", async () => {
    /** @type {Probe} */
    let picker;
    class Probe extends TimePicker {
        setup() {
            super.setup();
            picker = this;
        }
    }
    class Parent extends Component {
        static components = { TimePicker: Probe };
        static props = ["*"];
        static template = xml`<TimePicker value="'08:00'" showSeconds="this.state.showSeconds" minutesRounding="this.state.minutesRounding"/>`;
        setup() {
            this.state = useState({ showSeconds: false, minutesRounding: 5 });
        }
    }
    const parent = await mountWithCleanup(Parent);
    const initial = picker.suggestions;
    expect(initial.length).toBe(96);

    parent.state.showSeconds = true;
    await animationFrame();
    expect(picker.suggestions).toBe(initial);

    parent.state.minutesRounding = 1;
    await animationFrame();
    expect(picker.suggestions).toBe(initial);

    parent.state.minutesRounding = 30;
    await animationFrame();
    expect(picker.suggestions).not.toBe(initial);
    expect(picker.suggestions.length).toBe(48);
});

test("toggling showSeconds reformats the value already in the box", async () => {
    class Parent extends Component {
        static components = { TimePicker };
        static props = ["*"];
        static template = xml`<TimePicker value="'08:30:45'" showSeconds="this.state.showSeconds"/>`;
        setup() {
            this.state = useState({ showSeconds: false });
        }
    }
    const parent = await mountWithCleanup(Parent);
    expect("input.o_time_picker_input").toHaveValue("8:30");

    parent.state.showSeconds = true;
    await animationFrame();
    expect("input.o_time_picker_input").toHaveValue("8:30:45");

    parent.state.showSeconds = false;
    await animationFrame();
    expect("input.o_time_picker_input").toHaveValue("8:30");
});

test("an unfocused box resyncs to the value, so a rejected edit is recoverable", async () => {
    class Parent extends Component {
        static components = { TimePicker };
        static props = ["*"];
        static template = xml`<TimePicker value="this.state.value" onInvalid="() => this.onInvalid()"/>`;
        setup() {
            this.state = useState({ value: "08:30" });
        }
        onInvalid() {
            expect.step("invalid");
            this.render();
        }
    }
    await mountWithCleanup(Parent);
    await click("input.o_time_picker_input");
    await edit("nonsense", { confirm: "blur" });
    await animationFrame();

    expect.verifySteps(["invalid"]);
    expect("input.o_time_picker_input").toHaveValue("8:30");
});

test("a focused box keeps the user's keystrokes across an unrelated re-render", async () => {
    class Parent extends Component {
        static components = { TimePicker };
        static props = ["*"];
        static template = xml`<TimePicker value="'08:30'"/><span t-out="this.state.tick"/>`;
        setup() {
            this.state = useState({ tick: 0 });
        }
    }
    const parent = await mountWithCleanup(Parent);
    await click("input.o_time_picker_input");
    await edit("9:1");
    await animationFrame();
    expect("input.o_time_picker_input").toHaveValue("9:1");

    parent.state.tick++;
    await animationFrame();
    expect("input.o_time_picker_input").toHaveValue("9:1");
});

test("a browsed suggestion is committed when focus leaves the field", async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { TimePicker };
        static template = xml`
            <TimePicker value="'09:00'" onChange.bind="this.onChange"/>
            <input class="elsewhere"/>
        `;
        onChange(value) {
            expect.step(`change ${value.toString()}`);
        }
    }
    await mountWithCleanup(Parent);

    await click(".o_time_picker_input");
    await animationFrame();
    await press("arrowdown");
    await animationFrame();
    expect("input.o_time_picker_input").toHaveValue("9:15");

    queryOne(".elsewhere").focus();
    await animationFrame();
    expect.verifySteps(["change 9:15"]);
});

test("a browsed suggestion is committed on tab", async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { TimePicker };
        static template = xml`<TimePicker value="'09:00'" onChange.bind="this.onChange"/>`;
        onChange(value) {
            expect.step(`change ${value.toString()}`);
        }
    }
    await mountWithCleanup(Parent);

    await click(".o_time_picker_input");
    await animationFrame();
    await press("arrowdown");
    await press("arrowdown");
    await animationFrame();
    await press("tab");
    await animationFrame();
    expect.verifySteps(["change 9:30"]);
});

test("typing supersedes a browsed suggestion", async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { TimePicker };
        static template = xml`<TimePicker value="'09:00'" onChange.bind="this.onChange"/>`;
        onChange(value) {
            expect.step(`change ${value.toString()}`);
        }
    }
    await mountWithCleanup(Parent);

    await click(".o_time_picker_input");
    await animationFrame();
    await press("arrowdown");
    await animationFrame();
    await edit("11:45", { confirm: "enter" });
    await animationFrame();
    expect.verifySteps(["change 11:45"]);
});

test("typing with the menu open renders neither the picker nor its 96 options", async () => {
    let pickerRenders = 0;
    let itemRenders = 0;
    class Probe extends TimePicker {
        setup() {
            super.setup();
            onRendered(() => pickerRenders++);
        }
    }
    patchWithCleanup(DropdownItem.prototype, {
        setup() {
            super.setup();
            onRendered(() => itemRenders++);
        },
    });
    await mountWithCleanup(Probe, { props: { value: "12:00" } });
    await click(".o_time_picker_input");
    await animationFrame();
    expect(".o_time_picker_option").toHaveCount(96);

    pickerRenders = 0;
    itemRenders = 0;
    await edit("12:1", { confirm: false });
    await animationFrame();
    expect("input.o_time_picker_input").toHaveValue("12:1");
    expect(pickerRenders).toBe(0);
    expect(itemRenders).toBe(0);

    await press("ArrowDown");
    await animationFrame();
    expect("input.o_time_picker_input").toHaveValue("12:15");
    expect(pickerRenders).toBe(0);
});
