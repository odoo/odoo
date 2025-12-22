import { describe, expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "../_helpers/editor";
import { cleanLinkArtifacts, unformat } from "../_helpers/format";
import { animationFrame, click, select, waitFor, waitForNone } from "@odoo/hoot-dom";
import { getContent, simulateDoubleClickSelect } from "../_helpers/selection";
import { insertText } from "../_helpers/user_actions";
import { contains } from "@web/../tests/web_test_helpers";

describe("button style", () => {
    test("editable button should have cursor text", async () => {
        const { el } = await setupEditor(
            '<p><a href="#" class="btn btn-fill-primary">Link styled as button</a></p>'
        );

        const button = el.querySelector("a");
        expect(button).toHaveStyle({ cursor: "text" });
    });
    test("non-editable .btn-link should have cursor pointer", async () => {
        const { el } = await setupEditor(
            // A simpliflied version of an embedded component with toolbar
            // buttons, as it happens in certain flows in Knowledge.
            unformat(`
                <div contenteditable="false" data-embedded="clipboard">
                    <span class="o_embedded_toolbar">
                        <button class="btn">I am a button</button>
                    </span>
                </div>
            `)
        );
        const button = el.querySelector(".o_embedded_toolbar button");
        expect(button).toHaveStyle({ cursor: "pointer" });
    });

    test("Button styling should not override inner font size", async () => {
        const { el } = await setupEditor(
            unformat(`
                <div>
                    <span class="display-1-fs">a[b]c</span>
                </div>
            `)
        );
        await waitFor(".o-we-toolbar");
        await click("button[name='link']");
        await animationFrame();
        await click('select[name="link_type"]');
        await animationFrame();
        await select("primary");
        await animationFrame();
        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("#");

        // Ensure `.display-1-fs` overrides the `.btn`'s default font size.
        const link = el.querySelector("a.btn");
        const span = el.querySelector("span.display-1-fs");
        expect(getComputedStyle(link).fontSize).toBe(getComputedStyle(span).fontSize);

        expect(el).toHaveInnerHTML(
            unformat(`
                <div class="o-paragraph">
                    <span class="display-1-fs">a\ufeff<a class="btn btn-fill-primary" href="#">\ufeffb\ufeff</a>\ufeffc</span>
                </div>
            `)
        );
    });

    test("Should be able to change button style", async () => {
        await testEditor({
            contentBefore: unformat(`
                <div class="o-paragraph">
                    <span class="display-1-fs">a<a class="btn btn-fill-primary" href="#">[b]</a>c</span>
                </div>
            `),
            stepFunction: (editor) => {
                editor.shared.format.formatSelection("setFontSizeClassName", {
                    formatProps: { className: "h1-fs" },
                    applyStyle: true,
                });
            },
            contentAfter: unformat(`
                <div>
                    <span class="display-1-fs">
                        a
                        <a class="btn btn-fill-primary" href="#">
                            <span class="h1-fs">[b]</span>
                        </a>
                        c
                    </span>
                </div>
            `),
        });
    });
});

describe("button edit", () => {
    test("button link should be editable with double click select", async () => {
        const { el, editor } = await setupEditor('<p>this is a <a href="#">link</a></p>');
        await waitForNone(".o-we-linkpopover");
        const button = el.querySelector("a");
        // simulate double click selection
        await simulateDoubleClickSelect(button);
        expect(getContent(el)).toBe(
            '<p>this is a \ufeff<a href="#" class="o_link_in_selection">[\ufefflink]\ufeff</a>\ufeff</p>'
        );
        expect(cleanLinkArtifacts(getContent(el))).toBe('<p>this is a <a href="#">[link]</a></p>');
        await insertText(editor, "X");
        expect(cleanLinkArtifacts(getContent(el))).toBe('<p>this is a <a href="#">X[]</a></p>');
    });
});
