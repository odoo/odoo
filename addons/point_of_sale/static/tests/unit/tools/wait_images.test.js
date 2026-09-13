import { expect, microTick, test } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-mock";
import { waitImages } from "@point_of_sale/utils";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

function makeImages() {
    const container = document.createElement("div");
    container.innerHTML = "<img/><img/>";
    const images = [...container.children];
    for (const img of images) {
        Object.defineProperty(img, "complete", { value: false });
    }
    return { container, images };
}

test("repeated events on one image do not complete another image's wait", async () => {
    const { container, images } = makeImages();
    let settled = false;
    const waiting = waitImages(container).then((result) => {
        settled = true;
        return result;
    });
    images[0].dispatchEvent(new Event("load"));
    images[0].dispatchEvent(new Event("error"));
    await microTick();
    expect(settled).toBe(false);
    images[1].dispatchEvent(new Event("error"));
    expect(await waiting).toEqual({ timedOut: false });
});

test("image wait removes pending listeners on timeout", async () => {
    const { container, images } = makeImages();
    for (const img of images) {
        patchWithCleanup(img, {
            removeEventListener(type, callback) {
                expect.step(type);
                return super.removeEventListener(type, callback);
            },
        });
    }
    const waiting = waitImages(container, 100);
    await advanceTime(100);
    expect(await waiting).toEqual({ timedOut: true });
    expect.verifySteps(["load", "error", "load", "error"]);
});

test("independent image waiters settle and clean up at their own deadlines", async () => {
    const { container, images } = makeImages();
    const short = waitImages(container, 10);
    const long = waitImages(container, 100);
    await advanceTime(10);
    expect(await short).toEqual({ timedOut: true });
    images[0].dispatchEvent(new Event("load"));
    images[1].dispatchEvent(new Event("load"));
    expect(await long).toEqual({ timedOut: false });
});

test("loaded images need no listeners or timeout", async () => {
    const container = document.createElement("div");
    container.innerHTML = "<img/>";
    patchWithCleanup(container.firstChild, {
        addEventListener() {
            expect.step("listener");
        },
    });
    expect(await waitImages(container)).toEqual({ timedOut: false });
    expect.verifySteps([]);
});
