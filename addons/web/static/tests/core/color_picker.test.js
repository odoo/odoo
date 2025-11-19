import { test, expect, animationFrame } from "@odoo/hoot";
import { queryOne, manuallyDispatchProgrammaticEvent } from "@odoo/hoot-dom";
import { Component, useState, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { CustomColorPicker } from "@web/core/color_picker/custom_color_picker/custom_color_picker";

test("should preserve color slider when picking max lightness color", async () => {
    class TestColorPicker extends Component {
        static template = xml`
            <div style="width: 222px">
                <CustomColorPicker selectedColor="state.color" onColorPreview.bind="onColorChange" onColorSelect.bind="onColorChange"/>
            </div>`;
        static components = { CustomColorPicker };
        static props = ["*"];
        setup() {
            this.state = useState({
                color: "#FFFF00",
            });
        }
        onColorChange({ cssColor }) {
            this.state.color = cssColor;
        }
    }
    await mountWithCleanup(TestColorPicker);
    const colorPickerArea = queryOne(".o_color_pick_area");
    const colorPickerRect = colorPickerArea.getBoundingClientRect();

    const clientX = colorPickerRect.left + colorPickerRect.width / 2;
    const clientY = colorPickerRect.top; // Lightness 100%
    manuallyDispatchProgrammaticEvent(colorPickerArea, "mousedown", {
        clientX,
        clientY,
    });
    manuallyDispatchProgrammaticEvent(colorPickerArea, "mouseup", {
        clientX,
        clientY,
    });

    await animationFrame();
    expect(colorPickerArea).toHaveStyle({ backgroundColor: "rgb(255, 255, 0)" });
});
