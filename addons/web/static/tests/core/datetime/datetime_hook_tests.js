/** @odoo-module **/

import { Component, reactive, useState, xml } from "@odoo/owl";
import { clearRegistryWithCleanup, makeTestEnv } from "@web/../tests/helpers/mock_env";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import { editInput, getFixture, mount, nextTick } from "@web/../tests/helpers/utils";
import { datetimePickerService } from "@web/core/datetime/datetimepicker_service";
import { useDateTimePicker } from "@web/core/datetime/datetime_hook";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { popoverService } from "@web/core/popover/popover_service";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";

const { DateTime } = luxon;

/**
 * @param {() => any} setup
 */
const mountInput = async (setup) => {
    const env = await makeTestEnv();
    await mount(Root, getFixture(), { env, props: { setup } });
    return fixture.querySelector(".datetime_hook_input");
};

class Root extends Component {
    static components = { DateTimeInput };

    static template = xml`
        <input type="text" class="datetime_hook_input" t-ref="start-date" />
        <t t-foreach="mainComponentEntries" t-as="comp" t-key="comp[0]">
            <t t-component="comp[1].Component" t-props="comp[1].props" />
        </t>
    `;

    setup() {
        this.mainComponentEntries = mainComponentRegistry.getEntries();
        this.props.setup();
    }
}

const mainComponentRegistry = registry.category("main_components");
const serviceRegistry = registry.category("services");

let fixture;

QUnit.module("Components", ({ beforeEach }) => {
    beforeEach(() => {
        clearRegistryWithCleanup(mainComponentRegistry);

        serviceRegistry
            .add("hotkey", hotkeyService)
            .add(
                "localization",
                makeFakeLocalizationService({
                    dateFormat: "dd/MM/yyyy",
                    dateTimeFormat: "dd/MM/yyyy HH:mm:ss",
                })
            )
            .add("popover", popoverService)
            .add("ui", uiService)
            .add("datetime_picker", datetimePickerService);

        fixture = getFixture();
    });

    QUnit.module("DateTime hook");

    QUnit.test("reactivity: update inert object", async (assert) => {
        const pickerProps = {
            value: false,
            type: "date",
        };

        const input = await mountInput(() => {
            useDateTimePicker({ pickerProps });
        });

        assert.strictEqual(input.value, "");

        pickerProps.value = DateTime.fromSQL("2023-06-06");
        await nextTick();

        assert.strictEqual(input.value, "");
    });

    QUnit.test("reactivity: useState & update getter object", async (assert) => {
        const pickerProps = reactive({
            value: false,
            type: "date",
        });

        const input = await mountInput(() => {
            const state = useState(pickerProps);
            state.value; // artificially subscribe to value

            useDateTimePicker({
                get pickerProps() {
                    return pickerProps;
                },
            });
        });

        assert.strictEqual(input.value, "");

        pickerProps.value = DateTime.fromSQL("2023-06-06");
        await nextTick();

        assert.strictEqual(input.value, "06/06/2023");
    });

    QUnit.test("reactivity: update reactive object returned by the hook", async (assert) => {
        let pickerProps;
        const defaultPickerProps = {
            value: false,
            type: "date",
        };

        const input = await mountInput(() => {
            pickerProps = useDateTimePicker({ pickerProps: defaultPickerProps }).state;
        });

        assert.strictEqual(input.value, "");
        assert.strictEqual(pickerProps.value, false);

        pickerProps.value = DateTime.fromSQL("2023-06-06");
        await nextTick();

        assert.strictEqual(input.value, "06/06/2023");
    });

    QUnit.test("returned value is updated when input has changed", async (assert) => {
        let pickerProps;
        const defaultPickerProps = {
            value: false,
            type: "date",
        };

        const input = await mountInput(() => {
            pickerProps = useDateTimePicker({ pickerProps: defaultPickerProps }).state;
        });

        assert.strictEqual(input.value, "");
        assert.strictEqual(pickerProps.value, false);

        await editInput(input, null, "06/06/2023");

        assert.strictEqual(pickerProps.value.toSQL().split(" ")[0], "2023-06-06");
    });
});
