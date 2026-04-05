/** @odoo-module **/

import { expect, test } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { ToggleGroup, ToggleGroupItem } from "@odx_owl/components/toggle_group/toggle_group";

test("toggle group arrow navigation moves roving focus without changing pressed state", async () => {
    class Parent extends Component {
        static components = { ToggleGroup, ToggleGroupItem };
        static template = xml`
            <ToggleGroup defaultValue="'left'" loop="false" type="'single'">
                <ToggleGroupItem value="'left'">Left</ToggleGroupItem>
                <ToggleGroupItem value="'center'">Center</ToggleGroupItem>
                <ToggleGroupItem value="'right'">Right</ToggleGroupItem>
            </ToggleGroup>
        `;
    }

    await mountWithCleanup(Parent);

    expect(`[data-odx-toggle-group-item][data-value="left"]`).toHaveAttribute("aria-pressed", "true");
    expect(`[data-odx-toggle-group-item][data-value="center"]`).toHaveAttribute("aria-pressed", "false");
    expect(`[data-odx-toggle-group-item][data-value="left"]`).toHaveAttribute("tabindex", "0");

    await contains(`[data-odx-toggle-group-item][data-value="left"]`).focus();
    await contains(`[data-odx-toggle-group-item][data-value="left"]`).press("ArrowRight");

    expect(document.activeElement?.getAttribute("data-value")).toBe("center");
    expect(`[data-odx-toggle-group-item][data-value="left"]`).toHaveAttribute("aria-pressed", "true");
    expect(`[data-odx-toggle-group-item][data-value="center"]`).toHaveAttribute("aria-pressed", "false");
    expect(`[data-odx-toggle-group-item][data-value="center"]`).toHaveAttribute("tabindex", "0");

    await contains(`[data-odx-toggle-group-item][data-value="center"]`).click();

    expect(`[data-odx-toggle-group-item][data-value="left"]`).toHaveAttribute("aria-pressed", "false");
    expect(`[data-odx-toggle-group-item][data-value="center"]`).toHaveAttribute("aria-pressed", "true");
});
