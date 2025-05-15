import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";

defineWebsiteModels();

describe("useDomState", () => {
    test("Should not update the state of an async useDomState if a new step has been made", async () => {
        let currentResolve;
        addOption({
            selector: ".test-options-target",
            Component: class extends BaseOptionComponent {
                static template = xml`<div t-att-data-letter="getLetter()"/>`;
                setup() {
                    super.setup(...arguments);
                    this.state = useDomState(async () => {
                        const letter = await new Promise((resolve) => {
                            currentResolve = resolve;
                        });
                        return {
                            delay: `${letter}`,
                        };
                    });
                }
                getLetter() {
                    expect.step(`state: ${this.state.delay}`);
                    return this.state.delay;
                }
            },
        });
        const { getEditor } = await setupWebsiteBuilder(`<div class="test-options-target">a</div>`);
        await animationFrame();
        await contains(":iframe .test-options-target").click();
        const editor = getEditor();
        const resolve1 = currentResolve;
        resolve1("x");
        await animationFrame();

        editor.editable.querySelector(".test-options-target").textContent = "b";
        editor.shared.history.addStep();
        const resolve2 = currentResolve;
        editor.editable.querySelector(".test-options-target").textContent = "c";
        editor.shared.history.addStep();
        const resolve3 = currentResolve;

        resolve3("z");
        await animationFrame();
        resolve2("y");
        await animationFrame();
        expect.verifySteps(["state: x", "state: z"]);
    });
});
