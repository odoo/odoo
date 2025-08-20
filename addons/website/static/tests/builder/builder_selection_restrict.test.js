import { expect, test } from "@odoo/hoot";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { dummyBase64Img } from "@html_builder/../tests/helpers";
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

const blockquoteSnippet = unformat(`
    <section class="parent-target o_colored_level">
        <div class="container first-child">
            <blockquote class="s_blockquote o_colored_level o_draggable">
                <p class="p-target">p element in blockquote</p>
                <div class="s_blockquote_infos">
                    <img src="${dummyBase64Img}">
                    <div class="s_blockquote_author o-paragraph">
                        <span class="o_small">
                            <strong>Paul Dawson</strong><br>
                            <span class="text-muted">CEO of MyCompany</span>
                        </span>
                    </div>
                </div>
            </blockquote>
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
    });

    manuallyDispatchProgrammaticEvent(firstGrandchildEl, "mouseup", {
        detail: 1,
    });
    manuallyDispatchProgrammaticEvent(firstGrandchildEl, "click");
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
    });

    manuallyDispatchProgrammaticEvent(secondGrandchildEl, "mouseup", {
        detail: 1,
    });
    manuallyDispatchProgrammaticEvent(secondGrandchildEl, "click");
    await animationFrame();

    // The selection should be modified when it is outside the innermost
    // container.
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

    // Set the selection to be inside the first grandchild.
    setSelection({
        anchorNode: firstGrandchildEl.firstChild,
        anchorOffset: 4,
        focusOffset: 0,
    });

    manuallyDispatchProgrammaticEvent(firstGrandchildEl, "mouseup", {
        detail: 1,
    });
    manuallyDispatchProgrammaticEvent(firstGrandchildEl, "click");
    await animationFrame();

    // The selection should not be modified when it is inside the innermost
    // container.
    expect(getContent(editableContent)).toBe(
        unformat(
            `<section class="parent-target o_colored_level">
                <div class="child-target first-child">
                    <p class="grandchild-target first-grandchild">]firs[t grand child</p>
                </div>
                <div class="child-target second-child">
                    <p class="grandchild-target second-grandchild">second grand child</p>
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
    });

    manuallyDispatchProgrammaticEvent(secondGrandchildEl, "mouseup", {
        detail: 1,
    });
    manuallyDispatchProgrammaticEvent(secondGrandchildEl, "click");
    await animationFrame();

    // The selection should be modified when it is outside the innermost
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
});

test("selection restriction should be inside a <p> for special snippets - blockquote when pressing ctrl+a", async () => {
    const { getEditableContent, getEditor } = await setupWebsiteBuilder(blockquoteSnippet);
    const editableContent = getEditableContent();
    const editor = getEditor();
    const paragraphEl = editor.editable.querySelector("p.p-target");

    // Set the selection to be inside the p element.
    setSelection({
        anchorNode: paragraphEl.firstChild,
        anchorOffset: 0,
    });

    // Press ctrl+a to select all the content in the p element.
    await manuallyDispatchProgrammaticEvent(editor.editable, "keydown", {
        key: "a",
        ctrlKey: true,
    });

    expect(getContent(editableContent)).toBe(
        unformat(
            `<section class="parent-target o_colored_level" contenteditable="false">
                <div class="container first-child" contenteditable="true">
                    <blockquote class="s_blockquote o_colored_level o_draggable">
                        <p class="p-target">[p element in blockquote]</p>
                        <div class="s_blockquote_infos">
                            <img src="${dummyBase64Img}">
                            <div class="s_blockquote_author o-paragraph">
                                <span class="o_small">
                                    <strong>Paul Dawson</strong><br>
                                    <span class="text-muted">CEO of MyCompany</span>
                                </span>
                            </div>
                        </div>
                    </blockquote>
                </div>
            </section>`
        )
    );
});

test("selection restriction should be inside a <p> for special snippets - blockquote when selecting cross elements (left to right)", async () => {
    const { getEditableContent, getEditor } = await setupWebsiteBuilder(blockquoteSnippet);
    const editableContent = getEditableContent();
    const editor = getEditor();
    const paragraphEl = editor.editable.querySelector("p.p-target");
    const mutedEl = editor.editable.querySelector("span.text-muted");

    // Set the selection to be inside the p element.
    setSelection({
        anchorNode: paragraphEl.firstChild,
        anchorOffset: 0,
        focusNode: mutedEl.firstChild,
        focusOffset: 2,
    });

    manuallyDispatchProgrammaticEvent(mutedEl, "mouseup", {
        detail: 1,
    });
    manuallyDispatchProgrammaticEvent(mutedEl, "click");
    await animationFrame();

    expect(getContent(editableContent)).toBe(
        unformat(
            `<section class="parent-target o_colored_level" contenteditable="false">
                <div class="container first-child" contenteditable="true">
                    <blockquote class="s_blockquote o_colored_level o_draggable">
                        <p class="p-target">[p element in blockquote]</p>
                        <div class="s_blockquote_infos">
                            <img src="${dummyBase64Img}">
                            <div class="s_blockquote_author o-paragraph">
                                <span class="o_small">
                                    <strong>Paul Dawson</strong><br>
                                    <span class="text-muted">CEO of MyCompany</span>
                                </span>
                            </div>
                        </div>
                    </blockquote>
                </div>
            </section>`
        )
    );
});

test("selection restriction should be inside a <p> for special snippets - blockquote when selecting cross elements (right to left)", async () => {
    const { getEditableContent, getEditor } = await setupWebsiteBuilder(blockquoteSnippet);
    const editableContent = getEditableContent();
    const editor = getEditor();
    const paragraphEl = editor.editable.querySelector("p.p-target");
    const mutedEl = editor.editable.querySelector("span.text-muted");

    // Set the selection to be inside the p element.
    setSelection({
        anchorNode: mutedEl.firstChild,
        anchorOffset: 3,
        focusNode: paragraphEl.firstChild,
        focusOffset: 2,
    });

    manuallyDispatchProgrammaticEvent(mutedEl, "mouseup", {
        detail: 1,
    });
    manuallyDispatchProgrammaticEvent(mutedEl, "click");
    await animationFrame();

    expect(getContent(editableContent)).toBe(
        unformat(
            `<section class="parent-target o_colored_level" contenteditable="false">
                <div class="container first-child" contenteditable="true">
                    <blockquote class="s_blockquote o_colored_level o_draggable">
                        <p class="p-target">p element in blockquote</p>
                        <div class="s_blockquote_infos">
                            <img src="${dummyBase64Img}">
                            <div class="s_blockquote_author o-paragraph">
                                <span class="o_small">
                                    <strong>]Paul Dawson</strong><br>
                                    <span class="text-muted">CEO[ of MyCompany</span>
                                </span>
                            </div>
                        </div>
                    </blockquote>
                </div>
            </section>`
        )
    );
});
