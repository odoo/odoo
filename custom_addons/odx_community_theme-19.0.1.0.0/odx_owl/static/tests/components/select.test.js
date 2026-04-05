/** @odoo-module **/

import { expect, test } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { Select } from "@odx_owl/components/select/select";

test("closed select trigger uses repeated-character typeahead to cycle matches", async () => {
    class Parent extends Component {
        static components = { Select };
        static template = xml`<Select items="items" name="'framework'" />`;

        get items() {
            return [
                { label: "Alpha", value: "alpha" },
                { label: "Beta", value: "beta" },
                { label: "Bravo", value: "bravo" },
            ];
        }
    }

    await mountWithCleanup(Parent);

    await contains(`[role="combobox"]`).focus();
    await contains(`[role="combobox"]`).press("b");

    expect(`[role="combobox"]`).toHaveText("Beta");
    expect(document.querySelector(`input[type="hidden"][name="framework"]`)?.value).toBe("beta");

    await contains(`[role="combobox"]`).press("b");

    expect(`[role="combobox"]`).toHaveText("Bravo");
    expect(document.querySelector(`input[type="hidden"][name="framework"]`)?.value).toBe("bravo");
});
