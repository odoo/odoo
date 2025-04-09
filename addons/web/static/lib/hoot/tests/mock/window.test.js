/** @odoo-module */

import { after, describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { EventBus } from "@odoo/owl";
import { mountForTest, parseUrl } from "../local_helpers";
import { watchListeners } from "@odoo/hoot-mock";

describe(parseUrl(import.meta.url), () => {
    class TestBus extends EventBus {
        addEventListener(type) {
            expect.step(`addEventListener:${type}`);
            return super.addEventListener(...arguments);
        }

        removeEventListener() {
            throw new Error("Cannot remove event listeners");
        }
    }

    let testBus;

    test("elementFromPoint and elementsFromPoint should be mocked", async () => {
        await mountForTest(/* xml */ `
            <div class="oui" style="position: absolute; left: 10px; top: 10px; width: 250px; height: 250px;">
                Oui
            </div>
        `);

        expect(".oui").toHaveRect({
            x: 10,
            y: 10,
            width: 250,
            height: 250,
        });

        const div = queryOne(".oui");
        expect(document.elementFromPoint(11, 11)).toBe(div);
        expect(document.elementsFromPoint(11, 11)).toEqual([
            div,
            document.body,
            document.documentElement,
        ]);

        expect(document.elementFromPoint(9, 9)).toBe(document.body);
        expect(document.elementsFromPoint(9, 9)).toEqual([document.body, document.documentElement]);
    });

    // ! WARNING: the following 2 tests need to be run sequentially to work, as they
    // ! attempt to test the in-between-tests event listeners cleanup.
    test("event listeners are properly removed: setup", async () => {
        const callback = () => expect.step("callback");

        testBus = new TestBus();

        expect.verifySteps([]);

        after(watchListeners());

        testBus.addEventListener("some-event", callback);
        testBus.trigger("some-event");

        expect.verifySteps(["addEventListener:some-event", "callback"]);
    });
    test("event listeners are properly removed: check", async () => {
        testBus.trigger("some-event");

        expect.verifySteps([]);
    });
});
