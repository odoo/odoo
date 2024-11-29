/** @odoo-module */

import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { watchListeners } from "@odoo/hoot-mock";
import { EventBus } from "@odoo/owl";
import { mountForTest, parseUrl } from "../local_helpers";

describe(parseUrl(import.meta.url), () => {
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

    test("event listeners are properly removed", async () => {
        class MyBus extends EventBus {
            addEventListener(type) {
                expect.step(`add ${type}`);
                return super.addEventListener(...arguments);
            }

            removeEventListener() {
                throw new Error("Cannot remove event listeners");
            }
        }

        const unwatchListeners = watchListeners();

        const bus = new MyBus();
        const callback = () => expect.step("callback");

        expect.verifySteps([]);

        bus.addEventListener("some-event", callback);
        bus.trigger("some-event");

        expect.verifySteps(["add some-event", "callback"]);

        unwatchListeners();

        bus.trigger("some-event");

        expect.verifySteps([]);
    });
});
