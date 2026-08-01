import { initElementForEdition } from "@html_editor/utils/sanitize";
import { describe, expect, test } from "@odoo/hoot";

describe.current.tags("desktop");

const withImage = (attrs) => {
    const div = document.createElement("div");
    div.innerHTML = `<p><img src="/web/image/1" alt="x" ${attrs}></p>`;
    return div;
};

describe("initElementForEdition: forced image dimensions", () => {
    test("removeForcedImageDimensions moves width/height into an inline style", async () => {
        const div = withImage(`width="960" height="540"`);
        initElementForEdition(div, { removeForcedImageDimensions: true });
        const img = div.querySelector("img");
        expect(img.hasAttribute("width")).toBe(false);
        expect(img.hasAttribute("height")).toBe(false);
        expect(img.style.width).toBe("960px");
        expect(img.style.height).toBe("540px");
    });

    test("the attributes are left alone when the option is not set", async () => {
        // The default matters: outside `convert_inline` nothing re-applies them,
        // so stripping would permanently replace an author's intrinsic
        // dimensions with a fixed pixel size.
        const div = withImage(`width="960" height="540"`);
        initElementForEdition(div);
        const img = div.querySelector("img");
        expect(img.getAttribute("width")).toBe("960");
        expect(img.getAttribute("height")).toBe("540");
        expect(img.style.width).toBe("");
        expect(img.style.height).toBe("");
    });

    test("an image with no dimensions is untouched either way", async () => {
        for (const options of [{}, { removeForcedImageDimensions: true }]) {
            const div = withImage(`loading="lazy"`);
            initElementForEdition(div, options);
            const img = div.querySelector("img");
            expect(img.hasAttribute("width")).toBe(false);
            expect(img.style.width).toBe("");
        }
    });
});
