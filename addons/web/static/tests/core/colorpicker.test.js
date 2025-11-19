import { test, expect, animationFrame } from "@odoo/hoot";
import { queryOne, manuallyDispatchProgrammaticEvent } from "@odoo/hoot-dom";
import { Component, useState, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { Colorpicker } from "@web/core/colorpicker/colorpicker";

test("should preserve color slider when picking max lightness color", async () => {
    class TestColorPicker extends Component {
        static template = xml`
            <div style="width: 222px">
                <Colorpicker selectedColor="state.color" onColorPreview.bind="onColorChange" onColorSelect.bind="onColorChange"/>
            </div>`;
        static components = { Colorpicker };
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
