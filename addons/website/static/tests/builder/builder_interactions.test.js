import { beforeEach, expect, test } from "@odoo/hoot";
import { advanceTime, animationFrame, waitFor } from "@odoo/hoot-dom";
import { patch } from "@web/core/utils/patch"
import { contains, destroyApp, getService } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { Countdown } from "@website/snippets/s_countdown/countdown";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
    setupWebsiteBuilderWithSnippet,
} from "./website_helpers";

defineWebsiteModels();

class TestInteraction extends Interaction {
    static selector = ".test-target";
    dynamicContent = {
        _root: { "t-att-data-mode": () => this.mode },
    };
    get mode() {
        return "public";
    }
    start() {
        expect.step(`start ${this.mode}`);
    }
}

beforeEach(() => {
    registry.category("public.interactions").add("test.interaction", TestInteraction);
    registry.category("public.interactions.edit").add("test.interaction", {
        Interaction: TestInteraction,
        mixin: (I) =>
            class extends I {
                get mode() {
                    return "edit";
                }
            },
    });
});

test("public interactions run on the iframe content", async () => {
    await setupWebsiteBuilder(`<div class="test-target">a</div>`, {
        openEditor: false,
        interactions: ["test.interaction"],
    });
    expect.verifySteps(["start public"]);
    expect(":iframe .test-target").toHaveAttribute("data-mode", "public");
});

test("setup waits for asynchronous public interactions", async () => {
    const ready = Promise.withResolvers();
    const starting = Promise.withResolvers();
    patch(TestInteraction.prototype, {
        willStart() {
            starting.resolve();
            return ready.promise;
        },
    });
    let setupComplete = false;
    const setup = setupWebsiteBuilder(`<div class="test-target">a</div>`, {
        openEditor: false,
        interactions: ["test.interaction"],
    }).then(() => {
        setupComplete = true;
    });
    await starting.promise;
    await animationFrame();
    await animationFrame();
    expect(setupComplete).toBe(false);
    ready.resolve();
    await setup;
    expect.verifySteps(["start public"]);
    expect(":iframe .test-target").toHaveAttribute("data-mode", "public");
});

test("destroying the test app cleans up public interactions", async () => {
    patch(TestInteraction.prototype, {
        setup() {
            super.setup();
            this.registerCleanup(() => expect.step("cleanup"));
        },
        destroy() {
            expect.step("destroy");
        },
    });
    await setupWebsiteBuilder(`<div class="test-target">a</div>`, {
        openEditor: false,
        interactions: ["test.interaction"],
    });
    expect.verifySteps(["start public"]);
    destroyApp();
    expect.verifySteps(["cleanup", "destroy"]);
});

test("non white-listed public interactions never start on the parent document", async () => {
    class UnlistedInteraction extends Interaction {
        static selector = "body";
        start() {
            expect.step("unlisted interaction");
        }
    }
    registry.category("public.interactions").add("test.unlisted", UnlistedInteraction);
    await setupWebsiteBuilder(`<div class="test-target">a</div>`, {
        openEditor: false,
        interactions: ["test.interaction"],
    });
    expect.verifySteps(["start public"]);
});

test("edit interactions replace public ones when entering edit mode", async () => {
    const { openBuilderSidebar } = await setupWebsiteBuilder(
        `<div class="test-target">a</div>`,
        { openEditor: false, interactions: ["test.interaction"] }
    );
    expect.verifySteps(["start public"]);
    await openBuilderSidebar();
    await waitFor(":iframe .test-target[data-mode=edit]");
    expect.verifySteps(["start edit"]);
    expect(getService("public.interactions").interactions).toHaveLength(1);
});

test("interactions can be patched from the test", async () => {
    patch(TestInteraction.prototype, {
        get mode() {
            return "patched";
        },
    });
    await setupWebsiteBuilder(`<div class="test-target">a</div>`, {
        openEditor: false,
        interactions: ["test.interaction"],
    });
    expect.verifySteps(["start patched"]);
    expect(":iframe .test-target").toHaveAttribute("data-mode", "patched");
});

test("non white-listed interactions do not run", async () => {
    await setupWebsiteBuilderWithSnippet("s_countdown", { interactions: ["test.interaction"] });
    expect(getService("public.interactions").interactions).toHaveLength(0);
});

test("saving stops the edit interactions", async () => {
    await setupWebsiteBuilder(`<div class="test-target">a</div>`, {
        interactions: ["test.interaction"],
    });
    await waitFor(":iframe .test-target[data-mode=edit]");
    expect.verifySteps(["start public", "start edit"]);
    await contains("[data-action='save']").click();
    await waitFor(".o-website-builder_sidebar:not(.o_builder_sidebar_open)");
    expect(getService("public.interactions").interactions).toHaveLength(0);
});

test("countdown interaction renders with mocked timers in edit mode", async () => {
    patch(Countdown.prototype, {
        render() {
            expect.step("render");
            return super.render();
        },
    });
    await setupWebsiteBuilderWithSnippet("s_countdown", { interactions: ["website.countdown"] });
    await animationFrame();
    expect.verifySteps(["render", "render"]); // public then edit
    await advanceTime(2000);
    expect.verifySteps(["render", "render"]);
});
