/** @odoo-module */

import { getFixture } from "@web/../tests/helpers/utils";
import { htmlToCanvas } from "@point_of_sale/app/printer/render_service";

QUnit.module("RenderService", () => {
    QUnit.test("htmlToCanvas", async function (assert) {
        assert.expect(1);

        const target = getFixture();
        const node = document.createElement("div");
        node.classList.add("render-container");
        target.appendChild(node);
        
        const asciiChars = Array.from({length: 256}, (_, i) => String.fromCharCode(i)).join('');
        node.textContent = asciiChars;

        let canvas = null;
        try {
            canvas = await htmlToCanvas(node, { addClass: "pos-receipt-print" });
        } catch (error) {
            // htmlToCanvas create an <img> by setting a svg to its src attribute
            // if this fails, an Event of type "error" is thrown
            if (error.constructor.name !== "Event") {
                throw error;
            }
        }
        assert.notStrictEqual(canvas, null, `htmlToCanvas should work with all ascii characters`);
    });
});
