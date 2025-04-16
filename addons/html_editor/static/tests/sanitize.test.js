import { expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "./_helpers/editor";
import { Plugin } from "@html_editor/plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";

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

test("sanitize plugin should handle contenteditable attribute with o-contenteditable-[true/false] class", async () => {
    await testEditor({
        contentBefore: `<p class="o-contenteditable-true">a[]</p><p class="o-contenteditable-false">b</p>`,
        contentAfterEdit: `<p class="o-contenteditable-true" contenteditable="true">a[]</p><p class="o-contenteditable-false" contenteditable="false">b</p>`,
        contentAfter: `<p class="o-contenteditable-true">a[]</p><p class="o-contenteditable-false">b</p>`,
    });
});

test("sanitize plugin should handle role attribute with data-oe-role attribute", async () => {
    await testEditor({
        contentBefore: `<p data-oe-role="status">a[]</p>`,
        contentAfterEdit: `<p data-oe-role="status" role="status">a[]</p>`,
        contentAfter: `<p data-oe-role="status">a[]</p>`,
    });
});

test("sanitize plugin should handle aria-label attribute with data-oe-aria-label attribute", async () => {
    await testEditor({
        contentBefore: `<p data-oe-aria-label="status">a[]</p>`,
        contentAfterEdit: `<p data-oe-aria-label="status" aria-label="status">a[]</p>`,
        contentAfter: `<p data-oe-aria-label="status">a[]</p>`,
    });
});

test("should save without system_classes and system_attributes", async () => {
    await testEditor({
        contentBefore: `<p class="a foo" data-foo="test">hello[]</p>`,
        contentAfterEdit: `<p class="a foo" data-foo="test">hello[]</p>`,
        contentAfter: `<p class="a">hello[]</p>`,
        config: {
            Plugins: [
                ...MAIN_PLUGINS,
                class extends Plugin {
                    static id = "testPlugin";
                    resources = {
                        system_classes: "foo",
                        system_attributes: "data-foo",
                    };
                },
            ],
        },
    });
});
