import { expect, getFixture, test } from "@odoo/hoot";
import { mockFetch } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { htmlToCanvas, renderService } from "@point_of_sale/app/services/render_service";
import { clearRegistry, mountWithCleanup, patchTranslations } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";

test("test the render service", async () => {
    class ComponentToBeRendered extends Component {
        static props = ["name"];
        static template = xml`
                <div> It's me, <t t-esc="props.name" />! </div>
            `;
    }
    clearRegistry(registry.category("services"));
    clearRegistry(registry.category("main_components"));
    registry.category("services").add("render", renderService);

    patchTranslations(); // this is needed because we are not loading the localization service
    const comp = await mountWithCleanup("none");
    const renderedComp = await comp.env.services.render.toHtml(ComponentToBeRendered, {
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
