import { expect, test } from "@odoo/hoot";
import { setupEditor } from "./_helpers/editor";

test("sanitize should remove nasty elements", async () => {
    const { editor } = await setupEditor("");
    expect(editor.shared.sanitize.sanitize("<img src=x onerror=alert(1)//>")).toBe('<img src="x">');
    expect(editor.shared.sanitize.sanitize("<svg><g/onload=alert(2)//<p>")).toBe(
        "<svg><g></g></svg>"
    );
    expect(
        editor.shared.sanitize.sanitize("<p>abc<iframe//src=jAva&Tab;script:alert(3)>def</p>")
    ).toBe("<p>abc</p>");
});
