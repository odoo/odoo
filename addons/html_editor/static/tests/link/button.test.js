import { describe, expect, test } from "@odoo/hoot";
import { setupEditor } from "../_helpers/editor";
import { cleanLinkArtifacts, unformat } from "../_helpers/format";
import { waitForNone } from "@odoo/hoot-dom";
import { getContent, simulateDoubleClickSelect } from "../_helpers/selection";
import { insertText } from "../_helpers/user_actions";

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
