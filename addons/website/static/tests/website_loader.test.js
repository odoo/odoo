import { beforeEach, expect, test } from "@odoo/hoot";
import { animationFrame, delay, queryOne, waitFor } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { getService } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { WebsiteLoader } from "@website/components/website_loader/website_loader";

defineWebsiteModels();

let loaderInstance;
patch(WebsiteLoader.prototype, {
    setup() {
        super.setup();
        this.loaderCloseStepDelay = 0;
        this.loaderCloseFinalDelay = 500;
        loaderInstance = this;
    },

    advanceLoaderToNextStep() {
        const total = this.state.loadingSteps.length;
        const progressToReachNextStep = ((this.currentLoadingStepIndex + 1) / total) * 100;
        this.state.progressPercentage = progressToReachNextStep;
        this.updateLoadingSteps(progressToReachNextStep, total, 100 / total);
    },
});

const waitForLoaderCompletion = async ({
    completeRemainingProgress = true,
    totalSteps = 0,
    remainingSteps = 0,
}) => {
    if (completeRemainingProgress) {
        for (let i = 0; i < remainingSteps; i++) {
            await animationFrame();
        }
        expect(".o_website_loader_completed_step").toHaveCount(totalSteps);
        await delay(loaderInstance.loaderCloseFinalDelay);
    } else {
        await animationFrame();
    }
};

beforeEach(async () => {
    await setupWebsiteBuilder("", { openEditor: false });
    this.websiteService = getService("website");
});

test("should display loader correctly with default props", async () => {
    this.websiteService.showLoader();

    await waitFor(".o_website_loader_container");

    expect(".o_website_loader_title").toHaveText("Enhance your site in seconds.");
    expect(".o_website_loader_container_generic").toHaveCount(1);
    expect(".o_website_loader_completed_step").toHaveCount(0);
    expect(".o_website_loader_current_step").toHaveCount(0);
    expect(queryOne(".o_website_loader_bottom_message").children.length).toEqual(0);
    expect(".o_website_loader_progress").toHaveCount(1);
    expect("a .oi-close").toHaveCount(0);
});

test("should display loader correctly with custom props", async () => {
    this.websiteService.showLoader({
        title: "main title",
        flag: "colors",
        showCloseButton: true,
        bottomMessageTemplate: xml`<p class="test-message">My message</p>`,
        showProgressBar: false,
    });

    await waitFor(".o_website_loader_container");

    expect(".o_website_loader_title").toHaveText("main title");
    expect(".o_website_loader_container_colors").toHaveCount(1);
    expect(".o_website_loader_completed_step").toHaveCount(0);
    expect(".o_website_loader_current_step").toHaveCount(0);
    expect(".o_website_loader_bottom_message .test-message").toHaveCount(1);
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
    this.websiteService.showLoader({
        title: "main title",
        flag: "colors",
        loadingSteps,
    });

    await waitFor(".o_website_loader_container");

    // Stop automatic progress to control the progress manually.
    loaderInstance.clearLoaderInterval();

    // Step 1 has its own title and flag, so these should be displayed in the
    // loader.
    expect(".o_website_loader_title").toHaveText(loadingSteps[0].title);
    expect(`.o_website_loader_container_${loadingSteps[0].flag}`).toHaveCount(1);
    expect(".o_website_loader_completed_step").toHaveCount(0);
    expect(".o_website_loader_current_step").toHaveText(loadingSteps[0].description);

    loaderInstance.advanceLoaderToNextStep();
    await animationFrame();

    // Step 2 doesn't have its own title or flag, so the main title and flag
    // props will be displayed.
    expect(".o_website_loader_title").toHaveText("main title");
    expect(".o_website_loader_container_colors").toHaveCount(1);
    expect(".o_website_loader_completed_step").toHaveCount(1);
    expect(".o_website_loader_current_step").toHaveText("step 2 description");
});

test("should reflect externally updated progress in loader", async () => {
    let externalProgress = 0;
    function getExternalProgress() {
        return externalProgress;
    }

    this.websiteService.showLoader({
        getProgress: getExternalProgress,
    });

    await waitFor(".o_website_loader_container");

    expect(loaderInstance.state.progressPercentage).toBe(0);

    externalProgress = 20;
    // Wait 500ms because the loader updates progress percentage every 500ms.
    await delay(500);
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
    this.websiteService.showLoader({
        loadingSteps,
    });

    await waitFor(".o_website_loader_container");

    this.websiteService.hideLoader();

    await waitForLoaderCompletion({
        totalSteps: loadingSteps.length,
        remainingSteps: loadingSteps.length,
    });
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
    this.websiteService.showLoader({
        loadingSteps,
    });

    await waitFor(".o_website_loader_container");

    this.websiteService.hideLoader({ completeRemainingProgress: false });

    await waitForLoaderCompletion({
        completeRemainingProgress: false,
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
    this.websiteService.showLoader({
        loadingSteps,
    });

    await waitFor(".o_website_loader_container");

    this.websiteService.redirectOutFromLoader({
        url: "/test-url",
    });

    await waitForLoaderCompletion({
        totalSteps: loadingSteps.length,
        remainingSteps: loadingSteps.length,
    });
    expect(browser.location.href).toBe("https://www.hoot.test/test-url");
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
    this.websiteService.showLoader({
        loadingSteps,
    });

    await waitFor(".o_website_loader_container");

    this.websiteService.redirectOutFromLoader({
        url: "/test-url",
        completeRemainingProgress: false,
    });

    await waitForLoaderCompletion({
        completeRemainingProgress: false,
    });
    expect(browser.location.href).toBe("https://www.hoot.test/test-url");
});
