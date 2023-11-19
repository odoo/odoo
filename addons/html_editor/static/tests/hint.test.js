import { expect, test } from "@odoo/hoot";
import { setupEditor } from "./_helpers/editor";
import { getContent, setSelection } from "./_helpers/selection";
import { unformat } from "./_helpers/format";
import { animationFrame } from "@odoo/hoot-mock";

test("hints are removed when editor is destroyed", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>", {});
    expect(getContent(el)).toBe(`<p placeholder="Type "/" for commands" class="o-we-hint">[]</p>`);
    editor.destroy();
    expect(getContent(el)).toBe("<p>[]</p>");
});

test("should not lose track of temporary hints on split block", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>", {});
    expect(getContent(el)).toBe(`<p placeholder="Type "/" for commands" class="o-we-hint">[]</p>`);
    editor.dispatch("SPLIT_BLOCK");
    await animationFrame();
    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <p placeholder="Type "/" for commands" class="o-we-hint">[]<br></p>
        `)
    );
    const [firstP, secondP] = el.children;
    setSelection({ anchorNode: firstP, anchorOffset: 0, focusNode: firstP, focusOffset: 0 });
    await animationFrame();
    expect(getContent(el)).toBe(
        unformat(`
            <p placeholder="Type "/" for commands" class="o-we-hint">[]<br></p>
            <p><br></p>
        `)
    );
    setSelection({ anchorNode: secondP, anchorOffset: 0, focusNode: secondP, focusOffset: 0 });
    await animationFrame();
    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <p placeholder="Type "/" for commands" class="o-we-hint">[]<br></p>
        `)
    );
});

test("temporary hint should not be displayed where there's a permanent one", async () => {
    const { el, editor } = await setupEditor("<p>[]<br></p>", {});
    expect(getContent(el)).toBe(
        `<p placeholder="Type "/" for commands" class="o-we-hint">[]<br></p>`
    );
    editor.dispatch("SET_TAG", { tagName: "H1" });
    await animationFrame();
    // @todo @phoenix: getContent does not place the selection when anchor is BR
    expect(el.innerHTML).toBe(`<h1 placeholder="Heading 1" class="o-we-hint"><br></h1>`);
    editor.dispatch("SPLIT_BLOCK");
    await animationFrame();
    expect(getContent(el)).toBe(
        unformat(`
            <h1 placeholder="Heading 1" class="o-we-hint"><br></h1>
            <p placeholder="Type "/" for commands" class="o-we-hint">[]<br></p>
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
