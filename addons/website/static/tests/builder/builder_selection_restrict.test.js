import { expect, test } from "@odoo/hoot";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { getContent, setSelection } from "@html_editor/../tests/_helpers/selection";
import { manuallyDispatchProgrammaticEvent, animationFrame } from "@odoo/hoot-dom";
import { unformat } from "@html_editor/../tests/_helpers/format";

defineWebsiteModels();

const sectionSnippet = unformat(`
    <section class="parent-target o_colored_level">
        <div class="child-target first-child">
            <p class="grandchild-target first-grandchild">first grand child</p>
        </div>
        <div class="child-target second-child">
            <p class="grandchild-target second-grandchild">second grand child</p>
        </div>
    </section>
`);

test("the selection should be restricted in the closest div when pressing ctrl+a", async () => {
    const { getEditableContent, getEditor } = await setupWebsiteBuilder(sectionSnippet);
    const editableContent = getEditableContent();
    const editor = getEditor();
    const firstGrandchildEl = editor.editable.querySelector("p.first-grandchild");

    // Set the selection to be inside the first grandchild.
    setSelection({
        anchorNode: firstGrandchildEl.firstChild,
        anchorOffset: 0,
    });

    // Press ctrl+a to select all the content in the first grandchild.
    await manuallyDispatchProgrammaticEvent(editor.editable, "keydown", {
        key: "a",
        ctrlKey: true,
    });

    expect(getContent(editableContent)).toBe(
        unformat(
            `<section class="parent-target o_colored_level">
                <div class="child-target first-child">
                    <p class="grandchild-target first-grandchild">[first grand child]</p>
                </div>
                <div class="child-target second-child">
                    <p class="grandchild-target second-grandchild">second grand child</p>
                </div>
            </section>`
        )
    );
});

test("the selection should be restricted when it crosses different div from left to right", async () => {
    const { getEditableContent, getEditor } = await setupWebsiteBuilder(sectionSnippet);
    const editableContent = getEditableContent();
    const editor = getEditor();
    const firstGrandchildEl = editor.editable.querySelector("p.first-grandchild");
    const secondGrandchildEl = editor.editable.querySelector("p.second-grandchild");

    // Set the selection to be inside the first grandchild.
    setSelection({
        anchorNode: firstGrandchildEl.firstChild,
        anchorOffset: 0,
        focusOffset: 4,
        isMouseEventSimulated: true,
    });
    await animationFrame();

    // The selection should not be modified when it is inside the innermost
    // container.
    expect(getContent(editableContent)).toBe(
        unformat(
            `<section class="parent-target o_colored_level">
                <div class="child-target first-child">
                    <p class="grandchild-target first-grandchild">[firs]t grand child</p>
                </div>
                <div class="child-target second-child">
                    <p class="grandchild-target second-grandchild">second grand child</p>
                </div>
            </section>`
        )
    );

    // Set the selection across the two grandchildren
    setSelection({
        anchorNode: firstGrandchildEl.firstChild,
        anchorOffset: 0,
        focusNode: secondGrandchildEl.firstChild,
        focusOffset: 4,
        isMouseEventSimulated: true,
    });
    await animationFrame();

    // The selection should be modified when it is outside the innermost
    // container. It should be restricted to the first div.
    expect(getContent(editableContent)).toBe(
        unformat(
            `<section class="parent-target o_colored_level">
                <div class="child-target first-child">
                    <p class="grandchild-target first-grandchild">[first grand child]</p>
                </div>
                <div class="child-target second-child">
                    <p class="grandchild-target second-grandchild">second grand child</p>
                </div>
            </section>`
        )
    );
});

test("the selection should be restricted when it crosses different div from right to left", async () => {
    const { getEditableContent, getEditor } = await setupWebsiteBuilder(sectionSnippet);
    const editableContent = getEditableContent();
    const editor = getEditor();
    const firstGrandchildEl = editor.editable.querySelector("p.first-grandchild");
    const secondGrandchildEl = editor.editable.querySelector("p.second-grandchild");

    // Set the selection to be inside the second grandchild.
    setSelection({
        anchorNode: secondGrandchildEl.firstChild,
        anchorOffset: 4,
        focusOffset: 0,
        isMouseEventSimulated: true,
    });
    await animationFrame();

    // The selection should not be modified when it is inside the innermost
    // container.
    expect(getContent(editableContent)).toBe(
        unformat(
            `<section class="parent-target o_colored_level">
                <div class="child-target first-child">
                    <p class="grandchild-target first-grandchild">first grand child</p>
                </div>
                <div class="child-target second-child">
                    <p class="grandchild-target second-grandchild">]seco[nd grand child</p>
                </div>
            </section>`
        )
    );

    // Set the selection across the two grandchildren.
    setSelection({
        anchorNode: secondGrandchildEl.firstChild,
        anchorOffset: 4,
        focusNode: firstGrandchildEl.firstChild,
        focusOffset: 0,
        isMouseEventSimulated: true,
    });
    await animationFrame();

    // The selection should be modified when it is outside the innermost
    // container. It should be restricted to the first div.
    expect(getContent(editableContent)).toBe(
        unformat(
            `<section class="parent-target o_colored_level">
                <div class="child-target first-child">
                    <p class="grandchild-target first-grandchild">first grand child</p>
                </div>
                <div class="child-target second-child">
                    <p class="grandchild-target second-grandchild">]seco[nd grand child</p>
                </div>
            </section>`
        )
    );
});

test("the selection should be restricted to the innermost uncrossable element when it crosses nested uncrossable elements", async () => {
    const { getEditableContent, getEditor } = await setupWebsiteBuilder(
        unformat(`
            <div>
                <p>Text out of uncrossable element</p>
                <blockquote class="o_draggable">
                    <p class="text-in-uncrossable-element">Text in the parent uncrossable element (blockquote)</p>
                    <div class="s_blockquote_infos">
                        <span>
                            <strong>Text in the other uncrossable element (.s_blockquote_infos)</strong>
                        </span>
                    </div>
                </blockquote>
                <p class="text-out-of-uncrossable-element">Second text out of uncrossable element</p>
            </div>`)
    );
    const editableContent = getEditableContent();
    const editor = getEditor();
    const pInUncrossableEl = editor.editable.querySelector("p.text-in-uncrossable-element");
    const pOutofUncrossableEl = editor.editable.querySelector("p.text-out-of-uncrossable-element");

    // Set the selection across the uncrossable elements.
    setSelection({
        anchorNode: pInUncrossableEl.firstChild,
        anchorOffset: 6,
        focusNode: pOutofUncrossableEl.firstChild,
        focusOffset: 4,
        isMouseEventSimulated: true,
    });
    await animationFrame();

    // The selection should be restricted to the innermost uncrossable element.
    expect(getContent(editableContent)).toBe(
        unformat(
            `<div>
                <p>Text out of uncrossable element</p>
                <blockquote class="o_draggable">
                    <p class="text-in-uncrossable-element">Text i[n the parent uncrossable element (blockquote)]</p>
                    <div class="s_blockquote_infos">
                        <span>
                            <strong>Text in the other uncrossable element (.s_blockquote_infos)</strong>
                        </span>
                    </div>
                </blockquote>
                <p class="text-out-of-uncrossable-element">Second text out of uncrossable element</p>
            </div>`
        )
    );
});
