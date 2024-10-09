import { expect, test } from "@odoo/hoot";
import { animationFrame, click, waitFor } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { delay } from "@web/core/utils/concurrency";
import {
    addActionOption,
    addOption,
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "../../website_helpers";

defineWebsiteModels();

test("should commit changes", async () => {
    addActionOption({
        customAction: {
            getValue: ({ editingElement }) => editingElement.innerHTML,
            apply: ({ editingElement, value }) => {
                expect.step(`customAction ${value}`);
                editingElement.innerHTML = value;
            },
        },
    });
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderRange action="'customAction'" displayRangeValue="true"/>`,
    });
    await setupWebsiteBuilder(`
        <div class="test-options-target">10</div>
    `);
    await contains(":iframe .test-options-target").click();

    const input = await waitFor(".options-container input");
    input.value = 50;
    input.dispatchEvent(new Event("input"));
    await delay();
    input.dispatchEvent(new Event("change"));
    await delay();

    expect.verifySteps(["customAction 50", "customAction 50"]);
    expect(":iframe .test-options-target").toHaveInnerHTML("50");
    await click(document.body);
    await animationFrame();
    expect(".o-snippets-top-actions .fa-undo").toBeEnabled();
    expect(".o-snippets-top-actions .fa-repeat").not.toBeEnabled();
});
