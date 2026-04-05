/** @odoo-module **/

import { expect, test } from "@odoo/hoot";
import { Component, useState, xml } from "@odoo/owl";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { Checkbox } from "@odx_owl/components/checkbox/checkbox";

test("indeterminate checkbox toggles to checked and starts hidden form submission", async () => {
    class Parent extends Component {
        static components = { Checkbox };
        static template = xml`
            <Checkbox
                checked="state.checked"
                name="'terms'"
                onCheckedChange.bind="onCheckedChange"
            />
        `;

        setup() {
            this.state = useState({ checked: "indeterminate" });
        }

        onCheckedChange(checked) {
            this.state.checked = checked;
            expect.step(String(checked));
        }
    }

    await mountWithCleanup(Parent);

    expect(`[role="checkbox"]`).toHaveAttribute("aria-checked", "mixed");
    expect(`[role="checkbox"]`).toHaveAttribute("data-state", "indeterminate");
    expect(`input[type="hidden"][name="terms"]`).toHaveCount(0);

    await contains(`[role="checkbox"]`).click();

    expect.verifySteps(["true"]);
    expect(`[role="checkbox"]`).toHaveAttribute("aria-checked", "true");
    expect(`[role="checkbox"]`).toHaveAttribute("data-state", "checked");
    expect(`input[type="hidden"][name="terms"]`).toHaveCount(1);
    expect(document.querySelector(`input[type="hidden"][name="terms"]`)?.value).toBe("on");
});
