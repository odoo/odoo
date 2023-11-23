/** @odoo-module **/

import { Component, xml } from "@odoo/owl";
import { clearRegistryWithCleanup, makeTestEnv } from "@web/../tests/helpers/mock_env";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import { click, getFixture, mount } from "@web/../tests/helpers/utils";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { datetimePickerService } from "@web/core/datetime/datetimepicker_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { popoverService } from "@web/core/popover/popover_service";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";

const { DateTime } = luxon;

/**
 * @typedef {import("@web/core/datetime/datetime_input").DateTimeInputProps} DateTimeInputProps
 */

/**
 * @param {DateTimeInputProps} props
 */
const mountInput = async (props) => {
    const env = await makeTestEnv();
    await mount(Root, getFixture(), { env, props });
    return getFixture().querySelector(".o_datetime_input");
};

class Root extends Component {
    static components = { DateTimeInput };

    static template = xml`
        <div class="d-flex">
            <DateTimeInput t-props="props" />
        </div>
        <t t-foreach="mainComponentEntries" t-as="comp" t-key="comp[0]">
            <t t-component="comp[1].Component" t-props="comp[1].props" />
        </t>
    `;

    setup() {
        this.mainComponentEntries = mainComponentRegistry.getEntries();
    }
}

const mainComponentRegistry = registry.category("main_components");
const serviceRegistry = registry.category("services");

QUnit.module("Components", ({ beforeEach }) => {
    beforeEach(() => {
        clearRegistryWithCleanup(mainComponentRegistry);

        serviceRegistry
            .add("datetime_picker", datetimePickerService)
            .add("hotkey", hotkeyService)
            .add(
                "localization",
                makeFakeLocalizationService({
                    dateFormat: "dd/MM/yyyy",
                    dateTimeFormat: "dd/MM/yyyy HH:mm:ss",
                })
            )
            .add("popover", popoverService)
            .add("ui", uiService);
    });

    QUnit.module("DateTimeInput (date)");

    QUnit.test("popover should have enough space to be displayed", async (assert) => {
        const { parentElement: parent } = await mountInput({
            value: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy"),
            type: "date",
        });

        const initialParentRect = parent.getBoundingClientRect();

        await click(parent, ".o_datetime_input");

        const pickerRect = getFixture().querySelector(".o_datetime_picker").getBoundingClientRect();
        const finalParentRect = parent.getBoundingClientRect();

        assert.ok(
            initialParentRect.height < pickerRect.height,
            "initial height shouldn't be big enough to display the picker"
        );
        assert.ok(
            finalParentRect.height > pickerRect.height,
            "initial height should be big enough to display the picker"
        );
    });
});
