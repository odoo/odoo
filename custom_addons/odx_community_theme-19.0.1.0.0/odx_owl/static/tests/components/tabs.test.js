/** @odoo-module **/

import { expect, test } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@odx_owl/components/tabs/tabs";

test("manual tabs keep roving focus separate from selection and force-mount inactive content", async () => {
    class Parent extends Component {
        static components = { Tabs, TabsContent, TabsList, TabsTrigger };
        static template = xml`
            <Tabs activationMode="'manual'" defaultValue="'overview'">
                <TabsList>
                    <TabsTrigger value="'overview'">Overview</TabsTrigger>
                    <TabsTrigger value="'details'">Details</TabsTrigger>
                </TabsList>
                <TabsContent value="'overview'">Overview panel</TabsContent>
                <TabsContent value="'details'" forceMount="true">Details panel</TabsContent>
            </Tabs>
        `;
    }

    await mountWithCleanup(Parent);

    const panels = [...document.querySelectorAll('[role="tabpanel"]')];
    expect(panels.length).toBe(2);
    expect(panels[0].hidden).toBe(false);
    expect(panels[1].hidden).toBe(true);
    expect(`[role="tab"][data-value="overview"]`).toHaveAttribute("aria-selected", "true");
    expect(`[role="tab"][data-value="details"]`).toHaveAttribute("tabindex", "-1");

    await contains(`[role="tab"][data-value="overview"]`).focus();
    await contains(`[role="tab"][data-value="overview"]`).press("ArrowRight");

    expect(`[role="tab"][data-value="overview"]`).toHaveAttribute("aria-selected", "true");
    expect(`[role="tab"][data-value="details"]`).toHaveAttribute("tabindex", "0");
    expect(document.activeElement?.dataset.value).toBe("details");

    await contains(`[role="tab"][data-value="details"]`).press("Enter");

    expect(`[role="tab"][data-value="overview"]`).toHaveAttribute("aria-selected", "false");
    expect(`[role="tab"][data-value="details"]`).toHaveAttribute("aria-selected", "true");
    expect(panels[0].hidden).toBe(true);
    expect(panels[1].hidden).toBe(false);
});
