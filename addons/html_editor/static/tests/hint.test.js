import { expect, test } from "@odoo/hoot";
import { animationFrame, tick } from "@odoo/hoot-mock";
import { setupEditor } from "./_helpers/editor";
import { unformat } from "./_helpers/format";
import {
    getContent,
    moveSelectionOutsideEditor,
    setContent,
    setSelection,
} from "./_helpers/selection";
import { insertText } from "./_helpers/user_actions";

test("hints are removed when editor is destroyed", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>", {});
    expect(getContent(el)).toBe(`<p placeholder='Type "/" for commands' class="o-we-hint">[]</p>`);
    editor.destroy();
    expect(getContent(el)).toBe("<p>[]</p>");
});

test("powerbox hint is display when the selection is in the editor", async () => {
    const { el } = await setupEditor("<p></p>", {});
    expect(getContent(el)).toBe(`<p></p>`);

    setContent(el, "<p>[]</p>");
    await tick();
    expect(getContent(el)).toBe(`<p placeholder='Type "/" for commands' class="o-we-hint">[]</p>`);

    moveSelectionOutsideEditor();
    await tick();
    expect(getContent(el)).toBe(`<p></p>`);
});

test("placeholder is display when the selection is outside of the editor", async () => {
    const { el } = await setupEditor("<p></p>", { config: { placeholder: "test" } });
    expect(getContent(el)).toBe(`<p placeholder="test" class="o-we-hint"></p>`);

    setContent(el, "<p>[]</p>");
    await tick();
    expect(getContent(el)).toBe(`<p placeholder='Type "/" for commands' class="o-we-hint">[]</p>`);

    moveSelectionOutsideEditor();
    await tick();
    expect(getContent(el)).toBe(`<p placeholder="test" class="o-we-hint"></p>`);
});

test("placeholder must not be visible if there is content in the editor", async () => {
    const { el } = await setupEditor("<p></p><p>Hello</p>", { config: { placeholder: "test" } });
    expect(getContent(el)).toBe(`<p></p><p>Hello</p>`);
});

test("placeholder must not be visible if there is content in the editor (2)", async () => {
    const content =
        '<p><a href="#" title="document" data-mimetype="application/pdf" class="o_image" contenteditable="false"></a></p>';
    const { el } = await setupEditor(content, { config: { placeholder: "test" } });
    // Unchanged, no placeholder hint.
    expect(getContent(el)).toBe(content);
});

test("should not display hint in paragraph with media content", async () => {
    const content =
        '<p><a href="#" title="document" data-mimetype="application/pdf" class="o_image" contenteditable="false"></a>[]</p>';
    const { el } = await setupEditor(content);
    // Unchanged, no empty paragraph hint.
    expect(getContent(el)).toBe(content);
});

test("should not lose track of temporary hints on split block", async () => {
    const { el, editor, plugins } = await setupEditor("<p>[]</p>", {});
    expect(getContent(el)).toBe(`<p placeholder='Type "/" for commands' class="o-we-hint">[]</p>`);
    editor.shared.split.splitBlock();
    editor.shared.history.addStep();
    await animationFrame();
    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>
        `)
    );
    const [firstP, secondP] = el.children;
    setSelection({ anchorNode: firstP, anchorOffset: 0, focusNode: firstP, focusOffset: 0 });
    await animationFrame();
    expect(getContent(el)).toBe(
        unformat(`
            <p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>
            <p><br></p>
        `)
    );
    setSelection({ anchorNode: secondP, anchorOffset: 0, focusNode: secondP, focusOffset: 0 });
    await animationFrame();
    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>
        `)
    );
    // Changing the selection should not generate mutations for the next step
    expect(plugins.get("history").currentStep.mutations.length).toBe(0);
});

test("hint should only Be display for focused empty block element", async () => {
    const { el, editor } = await setupEditor("<p>[]<br></p>", {});
    expect(getContent(el)).toBe(
        `<p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>`
    );
    editor.shared.dom.setTag({ tagName: "H1" });
    await animationFrame();
    // @todo @phoenix: getContent does not place the selection when anchor is BR
    expect(el.innerHTML).toBe(`<h1 placeholder="Heading 1" class="o-we-hint"><br></h1>`);
    editor.shared.split.splitBlock();
    editor.shared.history.addStep();
    await animationFrame();
    expect(getContent(el)).toBe(
        unformat(`
            <h1><br></h1>
            <p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>
        `)
    );
    const h1 = el.firstElementChild;
    setSelection({ anchorNode: h1, anchorOffset: 0, focusNode: h1, focusOffset: 0 });
    await animationFrame();
    expect(getContent(el)).toBe(
        unformat(`
            <h1 placeholder="Heading 1" class="o-we-hint">[]<br></h1>
            <p><br></p>
        `)
    );
});

test("hint for code section should have the same padding as its text content", async () => {
    const { el, editor } = await setupEditor("<pre>[]</pre>");
    expect(getContent(el)).toBe(`<pre placeholder="Code" class="o-we-hint">[]</pre>`);
    const pre = el.firstElementChild;
    const hintStyle = getComputedStyle(pre, "::after");
    expect(hintStyle.content).toBe('"Code"');
    const paddingHint = hintStyle.padding;
    await insertText(editor, "abc");
    expect(hintStyle.content).toBe("none");
    const paddingText = getComputedStyle(pre).padding;
    expect(paddingHint).toBe(paddingText);
});

test("hint for blockquote should have the same padding as its text content", async () => {
    const { el, editor } = await setupEditor("<blockquote>[]</blockquote>");
    expect(getContent(el)).toBe(
        `<blockquote placeholder="Quote" class="o-we-hint">[]</blockquote>`
    );
    const blockquote = el.firstElementChild;
    const hintStyle = getComputedStyle(blockquote, "::after");
    expect(hintStyle.content).toBe('"Quote"');
    const paddingHint = hintStyle.padding;
    await insertText(editor, "abc");
    expect(hintStyle.content).toBe("none");
    const paddingText = getComputedStyle(blockquote).padding;
    expect(paddingHint).toBe(paddingText);
});
