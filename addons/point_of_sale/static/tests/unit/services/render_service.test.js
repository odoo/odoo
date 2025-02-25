import { describe, expect, getFixture, test } from "@odoo/hoot";
import { mockFetch } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { allowTranslations, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { htmlToCanvas } from "@point_of_sale/app/services/render_service";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();
odoo.pos_session_id = 1; // Ensure the session ID is set for lazy getters

describe("RenderService", () => {
    test("test the render service", async () => {
        class ComponentToBeRendered extends Component {
            static props = ["name"];
            static template = xml`
                <div> It's me, <t t-esc="props.name" />! </div>
            `;
        }

        allowTranslations(); // this is needed because we are not loading the localization service
        const comp = await mountWithCleanup("none");
        const renderedComp = await comp.env.services.renderer.toHtml(ComponentToBeRendered, {
            name: "Mario",
        });
        expect(renderedComp).toHaveOuterHTML("<div> It's me, Mario! </div>");
    });

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
});
