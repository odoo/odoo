import { test, expect } from "@odoo/hoot";
import { click, edit } from "@odoo/hoot-dom";
import { animationFrame, tick } from "@odoo/hoot-mock";
import { Component, reactive, useState, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { useDateTimePicker } from "@web/core/datetime/datetime_hook";
import { DateTimeInput } from "@web/core/datetime/datetime_input";

const { DateTime } = luxon;

/**
 * @param {() => any} setup
 */
const mountInput = async (setup) => {
    await mountWithCleanup(Root, { props: { setup } });
};

class Root extends Component {
    static components = { DateTimeInput };
    static template = xml`<input type="text" class="datetime_hook_input" t-ref="start-date"/>`;
    static props = ["*"];

    setup() {
        this.props.setup();
    }
}

test("reactivity: update inert object", async () => {
    const pickerProps = {
        value: false,
        type: "date",
    };

    await mountInput(() => {
        useDateTimePicker({ pickerProps });
    });

    expect(".datetime_hook_input").toHaveValue("");

    pickerProps.value = DateTime.fromSQL("2023-06-06");
    await tick();

    expect(".datetime_hook_input").toHaveText("");
});

test("reactivity: useState & update getter object", async () => {
    const pickerProps = reactive({
        value: false,
        type: "date",
    });

    await mountInput(() => {
        const state = useState(pickerProps);
        state.value; // artificially subscribe to value

        useDateTimePicker({
            get pickerProps() {
                return pickerProps;
            },
        });
    });

    expect(".datetime_hook_input").toHaveValue("");

    pickerProps.value = DateTime.fromSQL("2023-06-06");
    await animationFrame();

    expect(".datetime_hook_input").toHaveValue("06/06/2023");
});

test("reactivity: update reactive object returned by the hook", async () => {
    let pickerProps;
    const defaultPickerProps = {
        value: false,
        type: "date",
    };

    await mountInput(() => {
        pickerProps = useDateTimePicker({ pickerProps: defaultPickerProps }).state;
    });

    expect(".datetime_hook_input").toHaveValue("");
    expect(pickerProps.value).toBe(false);

    pickerProps.value = DateTime.fromSQL("2023-06-06");
    await tick();

    expect(".datetime_hook_input").toHaveValue("06/06/2023");
});

test("returned value is updated when input has changed", async () => {
    let pickerProps;
    const defaultPickerProps = {
        value: false,
        type: "date",
    };

    await mountInput(() => {
        pickerProps = useDateTimePicker({ pickerProps: defaultPickerProps }).state;
    });

    expect(".datetime_hook_input").toHaveValue("");
    expect(pickerProps.value).toBe(false);
    click(".datetime_hook_input");
    edit("06/06/2023");
    click(document.body);

    expect(pickerProps.value.toSQL().split(" ")[0]).toBe("2023-06-06");
});

test("value is not updated if it did not change", async () => {
    const getShortDate = (date) => date.toSQL().split(" ")[0];

    let pickerProps;
    const defaultPickerProps = {
        value: DateTime.fromSQL("2023-06-06"),
        type: "date",
    };

    await mountInput(() => {
        pickerProps = useDateTimePicker({
            pickerProps: defaultPickerProps,
            onApply: (value) => {
                expect.step(getShortDate(value));
            },
        }).state;
    });

    expect(".datetime_hook_input").toHaveValue("06/06/2023");
    expect(getShortDate(pickerProps.value)).toBe("2023-06-06");

    click(".datetime_hook_input");
    edit("06/06/2023");
    click(document.body);

    expect(getShortDate(pickerProps.value)).toBe("2023-06-06");
    expect([]).toVerifySteps();

    click(".datetime_hook_input");
    edit("07/07/2023");
    click(document.body);

    expect(getShortDate(pickerProps.value)).toBe("2023-07-07");
    expect(["2023-07-07"]).toVerifySteps();
});
