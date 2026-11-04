import { setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { describe, expect, test } from "@odoo/hoot";

describe.current.tags("desktop");

test("an uploaded font whose name contains a comma is a single font", async () => {
    const { getEditor } = await setupHTMLBuilder("<p>Test</p>", {
        styleContent: `:root {
            --number-of-fonts: 2;
            --font-number-1: 'Inter';
            --font-number-2: 'demo,font';
            --uploaded-local-fonts: ('demo,font': 42);
        }`,
    });

    const { uploadedLocalFonts, _fonts } = await getEditor().shared.builderFont.getFontsData();
    expect(uploadedLocalFonts).toEqual(["'demo,font': 42"]);
    // Only the uploaded font is deletable: the theme font keeps a negative
    // index, which is what hides its delete button.
    expect(_fonts.map((font) => [font.string, font.type, font.indexForType])).toEqual([
        ["Inter", "cloud", -1],
        ["demo,font", "uploaded", 0],
    ]);
});
