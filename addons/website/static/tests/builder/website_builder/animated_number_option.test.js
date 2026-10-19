import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { bold, setColor } from "@html_editor/../tests/_helpers/user_actions";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

async function setupAnimatedNumber() {
    const { getEditableContent, getEditor } = await setupWebsiteBuilderWithSnippet(
        "s_animated_number"
    );
    const editable = getEditableContent();
    const valueEl = editable.querySelector(".s_animated_number_value");
    valueEl.textContent = "1000";
    const displayEl = editable.querySelector(".s_animated_number_display");
    getEditor().shared.history.commit();
    return {
        displayEl,
        editor: getEditor(),
        valueEl,
    };
}

test("bold can be toggled on the animated number display", async () => {
    const { displayEl, editor, valueEl } = await setupAnimatedNumber();
    const valueTextNode = valueEl.firstChild;
    setSelection({
        anchorNode: valueTextNode,
        anchorOffset: 1,
        focusNode: valueTextNode,
        focusOffset: 3,
    });

    bold(editor);
    await animationFrame();
    expect(displayEl.style.getPropertyValue("font-weight")).toBe("");

    bold(editor);
    await animationFrame();
    expect(displayEl.style.getPropertyValue("font-weight")).toBe("bolder");
});

test("changing color on the animated number value only colors the number", async () => {
    const { editor, displayEl, valueEl } = await setupAnimatedNumber();
    const prefixTextNode = displayEl.ownerDocument.createTextNode("+");
    displayEl.prepend(prefixTextNode);

    const valueTextNode = valueEl.firstChild;
    setSelection({
        anchorNode: valueTextNode,
        anchorOffset: 0,
        focusNode: valueTextNode,
        focusOffset: 2,
    });

    setColor("#FF0000", "color")(editor);
    await animationFrame();
    expect(valueEl).toHaveStyle({ color: "rgb(255, 0, 0)" });
    expect(displayEl.style.getPropertyValue("color")).toBe("");
});

test("changing color on the whole animated number display colors the wrapper", async () => {
    const { editor, displayEl, valueEl } = await setupAnimatedNumber();
    const prefixTextNode = displayEl.ownerDocument.createTextNode("+");
    displayEl.prepend(prefixTextNode);

    const valueTextNode = valueEl.firstChild;
    setSelection({
        anchorNode: prefixTextNode,
        anchorOffset: 0,
        focusNode: valueTextNode,
        focusOffset: valueTextNode.length,
    });

    setColor("#00FF00", "color")(editor);
    await animationFrame();
    expect(displayEl).toHaveStyle({ color: "rgb(0, 255, 0)" });
    expect(valueEl).toHaveStyle({ color: "rgb(0, 255, 0)" });
});
