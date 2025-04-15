import { describe, expect, test } from "@odoo/hoot";
import { Deferred, delay, tick } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { Operation } from "../src/core/operation";
import {
    addActionOption,
    addOption,
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "./website_helpers";

describe("Operation", () => {
    test("handle 3 concurrent cancellable operations (with delay)", async () => {
        const operation = new Operation();
        function makeCall(data) {
            let resolve;
            const promise = new Promise((r) => {
                resolve = r;
            });
            async function load() {
                expect.step(`load before ${data}`);
                await promise;
                expect.step(`load after ${data}`);
            }
            function apply() {
                expect.step(`apply ${data}`);
            }

            operation.nextWithLoad(apply, { load, cancellable: true });
            return {
                resolve,
            };
        }
        const call1 = makeCall(1);
        await delay();
        const call2 = makeCall(2);
        await delay();
        const call3 = makeCall(3);
        await delay();
        call1.resolve();
        call2.resolve();
        call3.resolve();
        await operation.mutex.getUnlockedDef();
        expect.verifySteps([
            //
            "load before 1",
            "load after 1",
            "load before 3",
            "load after 3",
            "apply 3",
        ]);
    });
    test("handle 3 concurrent cancellable operations (without delay)", async () => {
        const operation = new Operation();
        function makeCall(data) {
            let resolve;
            const promise = new Promise((r) => {
                resolve = r;
            });
            async function load() {
                expect.step(`load before ${data}`);
                await promise;
                expect.step(`load after ${data}`);
            }
            function apply() {
                expect.step(`apply ${data}`);
            }

            operation.nextWithLoad(apply, { load, cancellable: true });
            return {
                resolve,
            };
        }
        const call1 = makeCall(1);
        const call2 = makeCall(2);
        const call3 = makeCall(3);
        call1.resolve();
        call2.resolve();
        call3.resolve();
        await operation.mutex.getUnlockedDef();
        expect.verifySteps(["load before 3", "load after 3", "apply 3"]);
    });
});

describe("Block editable", () => {
    defineWebsiteModels();

    test("Doing an operation should block the editable during its execution", async () => {
        const customActionDef = new Deferred();
        addActionOption({
            customAction: {
                load: () => customActionDef,
                apply: ({ editingElement }) => {
                    editingElement.classList.add("custom-action");
                },
            },
        });
        addOption({
            selector: ".test-options-target",
            template: xml`<BuilderButton action="'customAction'"/>`,
        });
        await setupWebsiteBuilder(`<div class="test-options-target">TEST</div>`, {
            loadIframeBundles: true,
        });

        await contains(":iframe .test-options-target").click();
        await contains("[data-action-id='customAction']").click();
        expect(":iframe .o_loading_screen:not(.o_we_ui_loading)").toHaveCount(1);
        await new Promise((resolve) => setTimeout(resolve, 600));
        expect(":iframe .o_loading_screen.o_we_ui_loading").toHaveCount(1);

        customActionDef.resolve();
        await tick();
        expect(":iframe .o_loading_screen.o_we_ui_loading").toHaveCount(0);
        expect(":iframe .test-options-target").toHaveClass("custom-action");
    });
});
