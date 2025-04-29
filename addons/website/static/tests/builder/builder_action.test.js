import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-dom";
import { useState, xml } from "@odoo/owl";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { WebsiteBuilder } from "@website/client_actions/website_preview/website_builder_action";
import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";

describe("website tests", () => {
    beforeEach(defineWebsiteModels);

    test("trigger mobile view", async () => {
        await setupWebsiteBuilder(`<h1> Homepage </h1>`);
        expect(".o_website_preview.o_is_mobile").toHaveCount(0);
        await contains("button[data-action='mobile']").click();
        expect(".o_website_preview.o_is_mobile").toHaveCount(1);
    });

    test("top window url in action context parameter", async () => {
        let websiteBuilder;
        patchWithCleanup(WebsiteBuilder.prototype, {
            setup() {
                websiteBuilder = this;
                this.props.action.context = {
                    params: {
                        path: "/web/content/",
                    },
                };
                super.setup();
            },
        });
        await setupWebsiteBuilder(`<h1> Homepage </h1>`);
        expect(websiteBuilder.initialUrl).toBe("/website/force/1?path=%2F");
    });
});

describe.tags("desktop");
describe("HTML builder tests", () => {
    beforeEach(() => {
        addBuilderAction({
            testAction: {
                isApplied: ({ editingElement }) => editingElement.classList.contains("applied"),
                apply: ({ editingElement }) => {
                    editingElement.classList.toggle("applied");
                    expect.step("apply");
                },
            },
        });
    });

    test("apply is called if clean is not defined", async () => {
        addBuilderOption({
            selector: ".s_test",
            template: xml`<BuilderButton action="'testAction'">Click</BuilderButton>`,
        });
        await setupHTMLBuilder(`<section class="s_test">Test</section>`);
        await contains(":iframe .s_test").click();
        await contains("[data-action-id='testAction']").click();
        expect("[data-action-id='testAction']").toHaveClass("active");
        expect.verifySteps(["apply", "apply"]); // preview, apply
        await contains("[data-action-id='testAction']").click();
        expect("[data-action-id='testAction']").not.toHaveClass("active");
        expect.verifySteps(["apply"]); // clean
    });

    test("custom action and shorthand action: clean actions are independent, apply is called on custom action if clean is not defined", async () => {
        addBuilderOption({
            selector: ".s_test",
            template: xml`<BuilderButton action="'testAction'" classAction="'custom-class'">Click</BuilderButton>`,
        });
        await setupHTMLBuilder(`<section class="s_test">Test</section>`);
        await contains(":iframe .s_test").click();
        await contains("[data-action-id='testAction']").click();
        expect("[data-action-id='testAction']").toHaveClass("active");
        expect.verifySteps(["apply", "apply"]); // preview, apply
        await contains("[data-action-id='testAction']").click();
        expect("[data-action-id='testAction']").not.toHaveClass("active");
        expect.verifySteps(["apply"]); // clean
    });

    test("Prepare is triggered on props updated", async () => {
        const newPropDeferred = new Deferred();
        let prepareDeferred = new Promise((r) => r());
        class TestOption extends BaseOptionComponent {
            static template = xml`<BuilderCheckbox action="'customAction'" actionParam="state.param"/>`;
            static props = {};
            setup() {
                super.setup();
                this.state = useState({ param: "old param" });
                newPropDeferred.then(() => {
                    this.state.param = "new param";
                });
            }
        }
        addBuilderAction({
            customAction: {
                prepare: async () => {
                    await prepareDeferred;
                    expect.step("prepare");
                },
                apply: () => {},
            },
        });
        addBuilderOption({
            OptionComponent: TestOption,
            selector: ".test-options-target",
        });
        await setupHTMLBuilder(`<section class="test-options-target">Homepage</section>`);
        await contains(":iframe .test-options-target").click();
        expect.verifySteps(["prepare"]);
        prepareDeferred = new Deferred();
        // Update prop
        newPropDeferred.resolve();
        await animationFrame();
        expect.verifySteps([]);
        prepareDeferred.resolve();
        await animationFrame();
        expect.verifySteps(["prepare"]);
    });
});
