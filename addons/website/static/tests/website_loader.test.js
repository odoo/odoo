import { before, beforeEach, describe, expect, test } from "@odoo/hoot";
import { advanceTime, animationFrame, queryOne, waitFor } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { getService, patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { WebsiteLoader } from "@website/components/website_loader/website_loader";

defineWebsiteModels();

describe("website loader", () => {
    let loaderInstance;
    let websiteService;
    const loaderTitleSelector = ".o_website_loader_container_content > .h4-fs";
    const completedStepsSelector = ".o_website_loader_tip:has(.fa-check)";
    const currentStepSelector = ".o_website_loader_tip:has(.fa-spin)";
    const bottomMessageContainerSelector = ".o_website_loader_container_content > p";

    const waitForLoaderCompletion = async ({
        completeRemainingProgress = true,
        totalSteps = 0,
        remainingSteps = 0,
    }) => {
        if (completeRemainingProgress) {
            for (let i = 0; i < remainingSteps; i++) {
                await animationFrame();
            }
            expect(completedStepsSelector).toHaveCount(totalSteps);
            expect(currentStepSelector).toHaveCount(0);
        } else {
            if (remainingSteps) {
                expect(currentStepSelector).toHaveCount(1);
            }
            await animationFrame();
        }
    };

    before(() => {
        patchWithCleanup(WebsiteLoader.prototype, {
            setup() {
                super.setup();
                this.stopProgressStepDelay = 0;
                this.stopProgressFinalPause = 0;
                loaderInstance = this;
            },
        });
    });
    beforeEach(async () => {
        await setupWebsiteBuilder("", { openEditor: false });
        websiteService = getService("website");
    });

    test("should display loader correctly with default props", async () => {
        websiteService.showLoader();

        await waitFor(".o_website_loader_container");

        expect(loaderTitleSelector).toHaveText("");
        expect(".o_website_loader_container_generic").toHaveCount(1);
        expect(completedStepsSelector).toHaveCount(0);
        expect(currentStepSelector).toHaveCount(0);
        expect(queryOne(bottomMessageContainerSelector).children.length).toEqual(0);
        expect(".o_website_loader_progress").toHaveCount(1);
        expect("a .oi-close").toHaveCount(0);
    });

    test("should display loader correctly with custom props", async () => {
        websiteService.showLoader({
            title: "main title",
            flag: "colors",
            showCloseButton: true,
            bottomMessageTemplate: xml`<p class="test-message">My message</p>`,
            showProgressBar: false,
        });

        await waitFor(".o_website_loader_container");

        expect(loaderTitleSelector).toHaveText("main title");
        expect(".o_website_loader_container_colors").toHaveCount(1);
        expect(completedStepsSelector).toHaveCount(0);
        expect(currentStepSelector).toHaveCount(0);
        expect(`${bottomMessageContainerSelector} .test-message`).toHaveCount(1);
        expect(".o_website_loader_progress").toHaveCount(0);
        expect("a .oi-close").toHaveCount(1);
    });

    test("should show custom loading steps with correct prop precedence", async () => {
        const loadingSteps = [
            {
                title: "step 1 title",
                description: "step 1 description",
                flag: "images",
            },
            {
                description: "step 2 description",
            },
        ];
        websiteService.showLoader({
            title: "main title",
            flag: "colors",
            loadingSteps,
        });

        await waitFor(".o_website_loader_container");

        // Stop automatic progress to control the progress manually.
        loaderInstance.clearLoaderInterval();

        // Step 1 has its own title and flag, so these should be displayed in
        // the loader.
        expect(loaderTitleSelector).toHaveText(loadingSteps[0].title);
        expect(`.o_website_loader_container_${loadingSteps[0].flag}`).toHaveCount(1);
        expect(completedStepsSelector).toHaveCount(0);
        expect(currentStepSelector).toHaveText(loadingSteps[0].description);

        // Advance loader to next step.
        loaderInstance.state.progressPercentage = 50;
        loaderInstance.updateLoadingSteps(50, 2, 50);
        await animationFrame();

        // Step 2 doesn't have its own title or flag, so the main title and flag
        // props will be displayed.
        expect(loaderTitleSelector).toHaveText("main title");
        expect(".o_website_loader_container_colors").toHaveCount(1);
        expect(completedStepsSelector).toHaveCount(1);
        expect(currentStepSelector).toHaveText(loadingSteps[1].description);
    });

    test("should reflect externally updated progress in loader", async () => {
        let externalProgress = 0;
        function getExternalProgress() {
            return externalProgress;
        }

        websiteService.showLoader({
            getProgress: getExternalProgress,
        });

        await waitFor(".o_website_loader_container");

        expect(loaderInstance.state.progressPercentage).toBe(0);

        externalProgress = 20;
        // Wait 500ms because the loader updates progress percentage every
        // 500ms.
        await advanceTime(500);
        expect(loaderInstance.state.progressPercentage).toBe(20);
    });

    test("should complete all remaining steps before closing loader", async () => {
        const loadingSteps = [
            {
                description: "step 1",
            },
            {
                description: "step 2",
            },
        ];
        websiteService.showLoader({
            loadingSteps,
        });

        await waitFor(".o_website_loader_container");

        // Small delay so the test can verify that all loader steps finish
        // before hiding the loader.
        loaderInstance.stopProgressFinalPause = 100;
        websiteService.hideLoader();

        await waitForLoaderCompletion({
            totalSteps: loadingSteps.length,
            remainingSteps: loadingSteps.length,
        });
        await advanceTime(loaderInstance.stopProgressFinalPause)
        expect(".o_website_loader_container").toHaveCount(0);
    });

    test("should close the loader immediately", async () => {
        const loadingSteps = [
            {
                description: "step 1",
            },
            {
                description: "step 2",
            },
        ];
        websiteService.showLoader({
            loadingSteps,
        });

        await waitFor(".o_website_loader_container");

        websiteService.hideLoader({ completeRemainingProgress: false });

        await waitForLoaderCompletion({
            completeRemainingProgress: false,
            totalSteps: loadingSteps.length,
            remainingSteps: loadingSteps.length,
        });
        expect(".o_website_loader_container").toHaveCount(0);
    });

    test("should complete all remaining steps before redirecting out of the loader", async () => {
        const loadingSteps = [
            {
                description: "step 1",
            },
            {
                description: "step 2",
            },
        ];
        websiteService.showLoader({
            loadingSteps,
        });

        await waitFor(".o_website_loader_container");

        websiteService.redirectOutFromLoader({
            redirectAction: () => {
                expect.step("redirect_action");
            },
        });

        await waitForLoaderCompletion({
            totalSteps: loadingSteps.length,
            remainingSteps: loadingSteps.length,
        });
        expect.verifySteps(["redirect_action"]);
    });

    test("should redirect out of the loader immediately", async () => {
        const loadingSteps = [
            {
                description: "step 1",
            },
            {
                description: "step 2",
            },
        ];
        websiteService.showLoader({
            loadingSteps,
        });

        await waitFor(".o_website_loader_container");

        websiteService.redirectOutFromLoader({
            redirectAction: () => {
                expect.step("redirect_action");
            },
            completeRemainingProgress: false,
        });

        await waitForLoaderCompletion({
            completeRemainingProgress: false,
            totalSteps: loadingSteps.length,
            remainingSteps: loadingSteps.length,
        });
        expect.verifySteps(["redirect_action"]);
    });

    test("should fallback to internal progress when external getProgress fails", async () => {
        patchWithCleanup(console, {
            warn: () => {
                expect.step("external_progress_failed");
            },
        });
        patchWithCleanup(WebsiteLoader.prototype, {
            calculateInternalProgress() {
                expect.step("internal_progress");
                return super.calculateInternalProgress(...arguments);
            },
        });

        websiteService.showLoader({
            getProgress: () => {
                throw new Error("External progress failed");
            },
        });

        await waitFor(".o_website_loader_container");
        expect(loaderInstance.state.progressPercentage).toBe(0);

        // Wait for the loader to attempt fetching external progress.
        await advanceTime(500);
        expect.verifySteps(["external_progress_failed", "internal_progress"]);
    });
});
