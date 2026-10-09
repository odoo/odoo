import { test, expect } from "@odoo/hoot";
import { animationFrame, click } from "@odoo/hoot-dom";
import { ColorPicker } from "@html_editor/components/color_picker/color_picker";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

test("custom gradient must be defined", async () => {
    await mountWithCleanup(ColorPicker, {
        props: {
            state: {
                selectedColor: "",
                defaultTab: "gradient",
            },
            applyColor() {},
            enabledTabs: ["gradient"],
        },
    });
    await click(".o_custom_gradient_button");
    await animationFrame();
    expect(".gradient-colors input[type='range']").toHaveCount(2);
});

async function openCustomGradient(type) {
    await mountWithCleanup(ColorPicker, {
        props: {
            state: {
                selectedColor: "",
                defaultTab: "gradient",
            },
            applyColor() {},
            enabledTabs: ["gradient"],
        },
    });
    await click(".o_custom_gradient_button");
    await animationFrame();
    if (type) {
        await click(`.o_type_row button:contains('${type}')`);
        await animationFrame();
    }
}

test.tags("desktop");
test("gradient type and size buttons specify aria-pressed", async () => {
    await openCustomGradient("Radial");
    expect(".o_type_row button:contains('Radial')").toHaveAttribute("aria-pressed", "true");
    expect(".o_type_row button:contains('Linear')").toHaveAttribute("aria-pressed", "false");
    expect(".o_type_row button:contains('Conic')").toHaveAttribute("aria-pressed", "false");
    expect(".o_radial_size_row button[aria-pressed='true']").toHaveCount(1);
    await click("button[title='Extend to the farthest corner']");
    await animationFrame();
    expect("button[title='Extend to the farthest corner']").toHaveAttribute("aria-pressed", "true");
    expect(".o_radial_size_row button[aria-pressed='true']").toHaveCount(1);
});
