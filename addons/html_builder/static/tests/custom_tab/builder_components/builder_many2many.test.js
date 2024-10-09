import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { xml } from "@odoo/owl";
import { delay } from "@web/core/utils/concurrency";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "../../website_helpers";

defineWebsiteModels();

test("many2many: find tag, select tag, unselect tag", async () => {
    onRpc("/web/dataset/call_kw/test/name_search", async (args) => [
        [1, "First"],
        [2, "Second"],
        [3, "Third"],
    ]);
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderMany2Many dataAttributeAction="'test'" model="'test'" limit="10"/>`,
    });
    const { getEditableContent } = await setupWebsiteBuilder(
        `<div class="test-options-target">b</div>`
    );
    const editableContent = getEditableContent();

    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    expect("table tr").toHaveCount(0);
    expect(editableContent).toHaveInnerHTML(`<div class="test-options-target">b</div>`);

    await contains(".btn.o-dropdown").click();
    expect("input").toHaveCount(1);
    await contains("input").click();
    await delay(300); // debounce
    await animationFrame();
    expect("span.o-dropdown-item").toHaveCount(3);
    await contains("span.o-dropdown-item").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="test-options-target" data-test="[{&quot;id&quot;:1,&quot;name&quot;:&quot;First&quot;}]">b</div>`
    );
    expect("table tr").toHaveCount(1);

    await contains(".btn.o-dropdown").click();
    await contains("input[placeholder]").click();
    await delay(300); // debounce
    await animationFrame();
    expect("span.o-dropdown-item").toHaveCount(2);
    await contains("span.o-dropdown-item").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="test-options-target" data-test="[{&quot;id&quot;:1,&quot;name&quot;:&quot;First&quot;},{&quot;id&quot;:2,&quot;name&quot;:&quot;Second&quot;}]">b</div>`
    );
    expect("table tr").toHaveCount(2);

    await contains("button.fa-minus").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="test-options-target" data-test="[{&quot;id&quot;:2,&quot;name&quot;:&quot;Second&quot;}]">b</div>`
    );
    expect("table tr").toHaveCount(1);
    expect("table input").toHaveValue("Second");
});
