import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { advanceTime } from "@odoo/hoot-dom";
import { DELAY_TOOLBAR_OPEN } from "@html_editor/main/toolbar/toolbar_plugin";
import { setSelection, simulateDoubleClickSelect } from "@html_editor/../tests/_helpers/selection";
import { bold, setColor, setFontSizeClassName } from "@html_editor/../tests/_helpers/user_actions";
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
    return {
        displayEl,
        editor: getEditor(),
        valueEl,
    };
}

test("bold can be toggled on the non-editable animated number value", async () => {
    const { editor, valueEl } = await setupAnimatedNumber();
    const valueTextNode = valueEl.firstChild;
    setSelection({
        anchorNode: valueTextNode,
        anchorOffset: 1,
        focusNode: valueTextNode,
        focusOffset: 3,
    });

    bold(editor);
    await animationFrame();
    expect(valueEl.style.getPropertyValue("font-weight")).toBe("");

    bold(editor);
    await animationFrame();
    expect(valueEl.style.getPropertyValue("font-weight")).toBe("bolder");
});

test("changing font size class on the non-editable value replaces the previous one", async () => {
    const { editor, valueEl } = await setupAnimatedNumber();
    const valueTextNode = valueEl.firstChild;
    setSelection({
        anchorNode: valueTextNode,
        anchorOffset: 1,
        focusNode: valueTextNode,
        focusOffset: 3,
    });

    setFontSizeClassName("h1-fs")(editor);
    await animationFrame();
    expect(valueEl.classList.contains("h1-fs")).toBe(true);
    expect(valueEl.classList.contains("h2-fs")).toBe(false);

    setFontSizeClassName("display-2-fs")(editor);
    await animationFrame();
    expect(valueEl.classList.contains("display-2-fs")).toBe(true);
    expect(valueEl.classList.contains("h1-fs")).toBe(false);
    expect(valueEl.textContent).toBe("1000");
});

test("selection inside the non-editable animated number value is not expanded", async () => {
    const { editor, valueEl } = await setupAnimatedNumber();
    const valueTextNode = valueEl.firstChild;
    setSelection({
        anchorNode: valueTextNode,
        anchorOffset: 1,
        focusNode: valueTextNode,
        focusOffset: 3,
    });

    editor.shared.selection.selectAroundNonEditable();
    const selection = editor.shared.selection.getEditableSelection();
    expect(selection.anchorNode).toBe(valueTextNode);
    expect(selection.anchorOffset).toBe(1);
    expect(selection.focusNode).toBe(valueTextNode);
    expect(selection.focusOffset).toBe(3);
});

test("changing color on a sized non-editable animated number value does not color its affixes", async () => {
    const { editor, displayEl, valueEl } = await setupAnimatedNumber();
    valueEl.classList.remove("h2-fs");
    valueEl.classList.add("h3-fs");
    const prefixTextNode = displayEl.ownerDocument.createTextNode("$");
    const prefixEl = displayEl.ownerDocument.createElement("span");
    prefixEl.classList.add("h3-fs");
    prefixEl.append(prefixTextNode);
    const postfixTextNode = displayEl.ownerDocument.createTextNode("+");
    displayEl.replaceChildren(prefixEl, valueEl, postfixTextNode);

    const valueTextNode = valueEl.firstChild;
    setSelection({
        anchorNode: valueTextNode,
        anchorOffset: 0,
        focusNode: valueTextNode,
        focusOffset: valueTextNode.length,
    });

    setColor("#FF0000", "color")(editor);
    await animationFrame();
    expect(valueEl).toHaveStyle({ color: "rgb(255, 0, 0)" });
    expect(prefixEl).not.toHaveStyle({ color: "rgb(255, 0, 0)" });
});

test("changing color on a sized animated number display colors selected affixes and value", async () => {
    const { editor, displayEl, valueEl } = await setupAnimatedNumber();
    valueEl.classList.remove("h2-fs");
    valueEl.classList.add("h3-fs");
    const prefixTextNode = displayEl.ownerDocument.createTextNode("$");
    const prefixEl = displayEl.ownerDocument.createElement("span");
    prefixEl.classList.add("h3-fs");
    prefixEl.append(prefixTextNode);
    const postfixTextNode = displayEl.ownerDocument.createTextNode("+");
    displayEl.replaceChildren(prefixEl, valueEl, postfixTextNode);

    setSelection({
        anchorNode: prefixTextNode,
        anchorOffset: 0,
        focusNode: postfixTextNode,
        focusOffset: postfixTextNode.length,
    });

    setColor("#00FF00", "color")(editor);
    await animationFrame();
    expect(valueEl).toHaveStyle({ color: "rgb(0, 255, 0)" });
    expect(prefixEl).toHaveStyle({ color: "rgb(0, 255, 0)" });
});

test("double clicking the non-editable animated number value opens the toolbar", async () => {
    const { valueEl } = await setupAnimatedNumber();

    await simulateDoubleClickSelect(valueEl);
    await advanceTime(DELAY_TOOLBAR_OPEN);
    await animationFrame();

    expect(".o-we-toolbar:not(.o_overlay_options)").toHaveCount(1);
});
