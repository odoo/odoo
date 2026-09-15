import { setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { expect, test, describe } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { queryOne } from "@odoo/hoot-dom";

describe.current.tags("desktop");

test("selection should be were clicked, even when clicking away from popover", async () => {
    const { getEditor } = await setupHTMLBuilder(
        `<section><div class="container">
            Apply color <i id="here">here</i>, then select <i id="there">there<i>.
        </div></section>`
    );
    const editor = getEditor();
    const hereEl = queryOne(":iframe #here");
    const thereEl = queryOne(":iframe #there");
    editor.shared.selection.setSelection({
        anchorNode: hereEl,
        anchorOffset: 0,
        focusNode: hereEl,
        focusOffset: 1,
    });
    await contains(".o-select-color-foreground").click();
    await contains(".custom-tab").click();
    expect(".o_color_pick_area").toBeVisible();
    await contains(".o_color_pick_area").click();

    thereEl.addEventListener(
        "pointerdown",
        () => {
            // Simulate change of selection when clicking inside iframe
            editor.shared.selection.setSelection({
                anchorNode: thereEl,
                anchorOffset: 0,
                focusNode: thereEl,
                focusOffset: 1,
            });
        },
        { capture: true }
    );
    await contains(thereEl).click();
    const selection = thereEl.ownerDocument.getSelection();
    expect(selection.anchorNode.parentElement).toBe(thereEl);
    expect(selection.focusNode.parentElement).toBe(thereEl);
});
