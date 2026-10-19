import { describe, expect, getFixture, test } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-mock";

describe("web/static/src/libs/bootstrap.js", () => {
    test("executeAfterTransition's fallback timer skips its callback once the element has been removed from the DOM", async () => {
        // `_queueCallback`/`executeAfterTransition` waits for a real
        // "transitionend" event, with a `setTimeout` fallback in case it
        // never fires. That timer isn't cancelled just because the element
        // got removed in the meantime (e.g. a template re-render discarding
        // it), so without the patch this callback would still run.
        const el = document.createElement("div");
        getFixture().append(el);

        let called = false;
        window.Index.executeAfterTransition(() => {
            called = true;
        }, el);
        el.remove();

        await advanceTime(1000);
        expect(called).toBe(false);
    });

    test("executeAfterTransition's fallback timer still runs its callback for an element still in the DOM", async () => {
        const el = document.createElement("div");
        getFixture().append(el);

        let called = false;
        window.Index.executeAfterTransition(() => {
            called = true;
        }, el);

        await advanceTime(1000);
        expect(called).toBe(true);
        el.remove();
    });

    test("a Modal's queued hide callback does not crash if its element is replaced before the transition ends (regression)", async () => {
        // Regression test for a runbot crash: website_slides' course review
        // tour posts/edits/deletes several reviews. Each cycle replaces the
        // whole modal subtree with a fresh element and disposes the
        // previous Modal instance. If an earlier cycle's own queued
        // "hide" fallback timer hadn't fired yet, it used to fire later
        // against the now disconnected, disposed instance:
        //   TypeError: Cannot read properties of null (reading 'ownerDocument')
        //       at Modal._resetAdjustments (...)
        const el = Object.assign(document.createElement("div"), {
            className: "modal",
            innerHTML: `<div class="modal-dialog"><div class="modal-content"><div class="modal-body"></div></div></div>`,
        });
        getFixture().append(el);
        const modal = new window.Modal(el);

        modal.show();
        await advanceTime(1000);

        modal.hide();
        // Simulate the element being discarded by a template re-render
        // before the queued hide callback's fallback timer fires.
        el.remove();

        await advanceTime(1000);
        expect(el.isConnected).toBe(false);
        modal.dispose();
    });
});
