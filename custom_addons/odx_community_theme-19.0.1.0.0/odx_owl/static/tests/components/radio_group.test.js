/** @odoo-module **/

import { expect, test } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { RadioGroup, RadioGroupItem } from "@odx_owl/components/radio_group/radio_group";

test("radio group skips disabled items and clamps at edges when looping is disabled", async () => {
    class Parent extends Component {
        static components = { RadioGroup, RadioGroupItem };
        static template = xml`
            <RadioGroup defaultValue="'alpha'" loop="false" name="'plan'" orientation="'horizontal'">
                <RadioGroupItem value="'alpha'" ariaLabel="'Alpha'"/>
                <RadioGroupItem value="'beta'" ariaLabel="'Beta'" disabled="true"/>
                <RadioGroupItem value="'gamma'" ariaLabel="'Gamma'"/>
            </RadioGroup>
        `;
    }

    await mountWithCleanup(Parent);

    expect(`[role="radio"][data-value="alpha"]`).toHaveAttribute("tabindex", "0");
    expect(`[role="radio"][data-value="alpha"]`).toHaveAttribute("aria-checked", "true");
    expect(document.querySelector(`input[type="hidden"][name="plan"]`)?.value).toBe("alpha");

    await contains(`[role="radio"][data-value="alpha"]`).focus();
    await contains(`[role="radio"][data-value="alpha"]`).press("ArrowRight");

    expect(document.activeElement?.getAttribute("data-value")).toBe("gamma");
    expect(`[role="radio"][data-value="gamma"]`).toHaveAttribute("aria-checked", "true");
    expect(`[role="radio"][data-value="gamma"]`).toHaveAttribute("tabindex", "0");
    expect(document.querySelector(`input[type="hidden"][name="plan"]`)?.value).toBe("gamma");

    await contains(`[role="radio"][data-value="gamma"]`).press("ArrowRight");

    expect(document.activeElement?.getAttribute("data-value")).toBe("gamma");
    expect(`[role="radio"][data-value="gamma"]`).toHaveAttribute("aria-checked", "true");
});
