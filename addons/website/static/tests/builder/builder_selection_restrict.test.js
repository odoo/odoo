import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { expect, test } from "@odoo/hoot";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { xml } from "@odoo/owl";

defineWebsiteModels();

test("the selection should be restricted to the element bond to the most inner container", async () => {
    addOption({
        selector: ".parent-target",
        template: xml`<BuilderRow label="'my label'">
                <BuilderButton applyTo="'.child-target'" classAction="'test-parent'"/>
            </BuilderRow>`,
    });
    addOption({
        selector: ".child-target",
        template: xml`<BuilderRow label="'my label'">
                <BuilderButton applyTo="'.grandchild-target'" classAction="'test-child'"/>
            </BuilderRow>`,
    });

    const { getEditableContent } = await setupWebsiteBuilder(
        `<section class="parent-target o_colored_level"><div class="child-target"><p class="grandchild-target">b</p></div></section>`
    );
    const editableContent = getEditableContent();
    await contains(":iframe .parent-target").click();
    // the contenteditable should not be manipulated when there is only one option container
    expect(editableContent).toHaveInnerHTML(
        `<section class="parent-target o_colored_level"><div class="child-target"><p class="grandchild-target">b</p></div></section>`
    );

    await contains(":iframe .child-target").click();
    // the contenteditable should be manipulated when there is more than one option container
    expect(editableContent).toHaveInnerHTML(
        `<section class="parent-target o_colored_level o_restricted_editable_area" contenteditable="false">
            <div class="child-target o_restricted_editable_area" contenteditable="true"><p class="grandchild-target">b</p></div>
        </section>`
    );

    const resultSave = [];
    onRpc("ir.ui.view", "save", ({ args }) => {
        resultSave.push(args[1]);
        return true;
    });

    await contains("[data-class-action='test-child']").click();
    expect(editableContent).toHaveInnerHTML(
        `<section class="parent-target o_colored_level o_restricted_editable_area" contenteditable="false">
            <div class="child-target o_restricted_editable_area" contenteditable="true"><p class="grandchild-target test-child">b</p></div>
        </section>`
    );
    expect("[data-class-action='test-child']").toHaveClass("active");
    expect("[data-class-action='test-child']").toHaveCount(1);

    // after save the contenteditable manipulation should be removed
    await contains(".o-snippets-top-actions button:contains(Save)").click();
    expect(resultSave[0]).toBe(
        `<div id="wrap" class="oe_structure oe_empty" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch"><section class="parent-target o_colored_level"><div class="child-target"><p class="grandchild-target test-child">b</p></div></section></div>`
    );
});
