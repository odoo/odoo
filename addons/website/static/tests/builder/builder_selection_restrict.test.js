import { expect, test } from "@odoo/hoot";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { dummyBase64Img } from "@html_builder/../tests/helpers";
import { getContent, setSelection } from "@html_editor/../tests/_helpers/selection";
import { manuallyDispatchProgrammaticEvent, animationFrame } from "@odoo/hoot-dom";

defineWebsiteModels();

test("the selection should be restricted in the closest div when press ctrl+a", async () => {
    const { getEditableContent, getEditor } = await setupWebsiteBuilder(
        `<section class="parent-target o_colored_level">
            <div class="child-target first-child">
                <p class="grandchild-target first-grandchild">first grand child</p>
            </div>
            <div class="child-target second-child">
                <p class="grandchild-target second-grandchild">second grand child</p>
            </div>
        </section>`
    );
    const editableContent = getEditableContent();
    const editor = getEditor();
    const first_grandchild = editor.editable.querySelector("p.first-grandchild");

    // set the selection to be inside the first grandchild
    setSelection({
        anchorNode: first_grandchild.firstChild,
        anchorOffset: 0,
    });

    // press ctrl+a to select all the content in the first grandchild
    await manuallyDispatchProgrammaticEvent(editor.editable, "keydown", {
        key: "a",
        ctrlKey: true,
    });

    expect(getContent(editableContent)).toBe(
        `<section class="parent-target o_colored_level">
            <div class="child-target first-child">
                <p class="grandchild-target first-grandchild">[first grand child]</p>
            </div>
            <div class="child-target second-child">
                <p class="grandchild-target second-grandchild">second grand child</p>
            </div>
        </section>`
    );
});

test("the selection should be restricted when it acrosses different div from left to right", async () => {
    const { getEditableContent, getEditor } = await setupWebsiteBuilder(
        `<section class="parent-target o_colored_level">
            <div class="child-target first-child">
                <p class="grandchild-target first-grandchild">first grand child</p>
            </div>
            <div class="child-target second-child">
                <p class="grandchild-target second-grandchild">second grand child</p>
            </div>
        </section>`
    );
    const editableContent = getEditableContent();
    const editor = getEditor();
    const first_grandchild = editor.editable.querySelector("p.first-grandchild");
    const second_grandchild = editor.editable.querySelector("p.second-grandchild");

    // set the selection to be inside the first grandchild
    setSelection({
        anchorNode: first_grandchild.firstChild,
        anchorOffset: 0,
        focusOffset: 4,
    });

    manuallyDispatchProgrammaticEvent(first_grandchild, "mouseup", {
        detail: 1,
    });
    manuallyDispatchProgrammaticEvent(first_grandchild, "click");
    await animationFrame();

    // the selection should be not be modified when it is inside the most inner container
    expect(getContent(editableContent)).toBe(
        `<section class="parent-target o_colored_level">
            <div class="child-target first-child">
                <p class="grandchild-target first-grandchild">[firs]t grand child</p>
            </div>
            <div class="child-target second-child">
                <p class="grandchild-target second-grandchild">second grand child</p>
            </div>
        </section>`
    );

    // set the selection across the two grandchildren
    setSelection({
        anchorNode: first_grandchild.firstChild,
        anchorOffset: 0,
        focusNode: second_grandchild.firstChild,
        focusOffset: 4,
    });

    manuallyDispatchProgrammaticEvent(second_grandchild, "mouseup", {
        detail: 1,
    });
    manuallyDispatchProgrammaticEvent(second_grandchild, "click");
    await animationFrame();

    // the selection should be modified when it is outside the most inner container
    expect(getContent(editableContent)).toBe(
        `<section class="parent-target o_colored_level">
            <div class="child-target first-child">
                <p class="grandchild-target first-grandchild">[first grand child]</p>
            </div>
            <div class="child-target second-child">
                <p class="grandchild-target second-grandchild">second grand child</p>
            </div>
        </section>`
    );
});

test("the selection should be restricted when it acrosses different div from right to left", async () => {
    const { getEditableContent, getEditor } = await setupWebsiteBuilder(
        `<section class="parent-target o_colored_level">
            <div class="child-target first-child">
                <p class="grandchild-target first-grandchild">first grand child</p>
            </div>
            <div class="child-target second-child">
                <p class="grandchild-target second-grandchild">second grand child</p>
            </div>
        </section>`
    );
    const editableContent = getEditableContent();
    const editor = getEditor();
    const first_grandchild = editor.editable.querySelector("p.first-grandchild");
    const second_grandchild = editor.editable.querySelector("p.second-grandchild");

    // set the selection to be inside the first grandchild
    setSelection({
        anchorNode: first_grandchild.firstChild,
        anchorOffset: 4,
        focusOffset: 0,
    });

    manuallyDispatchProgrammaticEvent(first_grandchild, "mouseup", {
        detail: 1,
    });
    manuallyDispatchProgrammaticEvent(first_grandchild, "click");
    await animationFrame();

    // the selection should be not be modified when it is inside the most inner container
    expect(getContent(editableContent)).toBe(
        `<section class="parent-target o_colored_level">
            <div class="child-target first-child">
                <p class="grandchild-target first-grandchild">]firs[t grand child</p>
            </div>
            <div class="child-target second-child">
                <p class="grandchild-target second-grandchild">second grand child</p>
            </div>
        </section>`
    );

    // set the selection across the two grandchildren
    setSelection({
        anchorNode: second_grandchild.firstChild,
        anchorOffset: 4,
        focusNode: first_grandchild.firstChild,
        focusOffset: 0,
    });

    manuallyDispatchProgrammaticEvent(second_grandchild, "mouseup", {
        detail: 1,
    });
    manuallyDispatchProgrammaticEvent(second_grandchild, "click");
    await animationFrame();

    // the selection should be modified when it is outside the most inner container
    expect(getContent(editableContent)).toBe(
        `<section class="parent-target o_colored_level">
            <div class="child-target first-child">
                <p class="grandchild-target first-grandchild">first grand child</p>
            </div>
            <div class="child-target second-child">
                <p class="grandchild-target second-grandchild">]seco[nd grand child</p>
            </div>
        </section>`
    );
});

test("selection restriction should be inside a <p> for special snippets - blockquote when pressing ctrl+a", async () => {
    const { getEditableContent, getEditor } = await setupWebsiteBuilder(
        `<section class="parent-target o_colored_level">
            <div class="container first-child">
                <blockquote>
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
        </section>`
    );
    const editableContent = getEditableContent();
    const editor = getEditor();
    const p_element = editor.editable.querySelector("p.p-target");

    // set the selection to be inside the p element
    setSelection({
        anchorNode: p_element.firstChild,
        anchorOffset: 0,
    });

    // press ctrl+a to select all the content in the p element
    await manuallyDispatchProgrammaticEvent(editor.editable, "keydown", {
        key: "a",
        ctrlKey: true,
    });

    expect(getContent(editableContent)).toBe(
        `<section class="parent-target o_colored_level" contenteditable="false">
            <div class="container first-child" contenteditable="true">
                <blockquote>
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
    );
});

test("selection restriction should be inside a <p> for special snippets - blockquote when selecting cross elements (left to right)", async () => {
    const { getEditableContent, getEditor } = await setupWebsiteBuilder(
        `<section class="parent-target o_colored_level">
            <div class="container first-child">
                <blockquote class="o_draggable">
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
        </section>`
    );
    const editableContent = getEditableContent();
    const editor = getEditor();
    const p_element = editor.editable.querySelector("p.p-target");
    const muted_element = editor.editable.querySelector("span.text-muted");

    // set the selection to be inside the p element
    setSelection({
        anchorNode: p_element.firstChild,
        anchorOffset: 0,
        focusNode: muted_element.firstChild,
        focusOffset: 2,
    });

    manuallyDispatchProgrammaticEvent(muted_element, "mouseup", {
        detail: 1,
    });
    manuallyDispatchProgrammaticEvent(muted_element, "click");
    await animationFrame();

    expect(getContent(editableContent)).toBe(
        `<section class="parent-target o_colored_level" contenteditable="false">
            <div class="container first-child" contenteditable="true">
                <blockquote class="o_draggable">
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
    );
});

test("selection restriction should be inside a <p> for special snippets - blockquote when selecting cross elements (right to left)", async () => {
    const { getEditableContent, getEditor } = await setupWebsiteBuilder(
        `<section class="parent-target o_colored_level">
            <div class="container first-child">
                <blockquote class="o_draggable">
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
        </section>`
    );
    const editableContent = getEditableContent();
    const editor = getEditor();
    const p_element = editor.editable.querySelector("p.p-target");
    const muted_element = editor.editable.querySelector("span.text-muted");

    // set the selection to be inside the p element
    setSelection({
        anchorNode: muted_element.firstChild,
        anchorOffset: 3,
        focusNode: p_element.firstChild,
        focusOffset: 2,
    });

    manuallyDispatchProgrammaticEvent(muted_element, "mouseup", {
        detail: 1,
    });
    manuallyDispatchProgrammaticEvent(muted_element, "click");
    await animationFrame();

    expect(getContent(editableContent)).toBe(
        `<section class="parent-target o_colored_level" contenteditable="false">
            <div class="container first-child" contenteditable="true">
                <blockquote class="o_draggable">
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
    );
});
