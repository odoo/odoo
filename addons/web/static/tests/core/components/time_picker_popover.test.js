import { Component, xml } from "@odoo/owl";
import { expect, getFixture, test } from "@odoo/hoot";
import { mountWithCleanup } from "../../web_test_helpers";
import { usePopover } from "@web/core/popover/popover_hook";
import { TimePickerPopover } from "@web/core/time_picker/time_picker_popover";
import { animationFrame, click } from "@odoo/hoot-dom";

test("timepicker popover can be used with popover service", async () => {
    class Button extends Component {
        static template = xml`<button class="test-btn" t-on-click="this.onClick">Click</button>`;

        setup() {
            this.picker = usePopover(TimePickerPopover);
        }

        onClick() {
            this.picker.open(getFixture(), {
                pickerProps: {
                    value: "12:30",
                },
            });
        }
    }

    await mountWithCleanup(Button);
    await click(".test-btn");
    await animationFrame();

    expect(".o_time_picker").toHaveCount(1);
});
