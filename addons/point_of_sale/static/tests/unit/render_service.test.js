import { expect, getFixture, test } from "@odoo/hoot";
import { mockFetch } from "@odoo/hoot-mock";
import { htmlToCanvas } from "@point_of_sale/app/printer/render_service";

test("htmlToCanvas", async () => {
    // htmlToCanvas fetches some fonts useless for the test, we mock it to avoid warnings
    mockFetch(() => "");
    const target = getFixture();
    const node = document.createElement("div");
    node.classList.add("render-container");
    target.appendChild(node);

    const asciiChars = Array.from({ length: 256 }, (_, i) => String.fromCharCode(i)).join("");
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
    expect(canvas).not.toBe(null, {
        message: "htmlToCanvas should work with all ascii characters",
    });
});
