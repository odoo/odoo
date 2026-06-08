import { expect, test } from "@odoo/hoot";
import { click, press, queryOne, waitFor, waitForNone } from "@odoo/hoot-dom";
import { animationFrame, tick } from "@odoo/hoot-mock";
import { contains } from "@web/../tests/web_test_helpers";
import { setupEditor } from "../_helpers/editor";
import { cleanLinkArtifacts } from "../_helpers/format";
import { getContent, setContent, setSelection } from "../_helpers/selection";
import { undo } from "../_helpers/user_actions";
import { expectElementCount } from "../_helpers/ui_expectations";
import { execCommand } from "../_helpers/userCommands";

const base64Img =
    "data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAAUA\n        AAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO\n            9TXL0Y4OHwAAAABJRU5ErkJggg==";

test("can add link to inline image + text", async () => {
    const { el } = await setupEditor(`<p>ab[cd<img src="${base64Img}">ef]g</p>`);
    await waitFor(".o-we-toolbar");
    await click(".o-we-toolbar .fa-link");
    await contains(".o-we-linkpopover input.o_we_href_input_link", { timeout: 1500 }).edit(
        "http://test.test/"
    );
    expect(cleanLinkArtifacts(getContent(el))).toBe(
        `<p>ab<a href="http://test.test/">cd<img src="${base64Img}">ef[]</a>g</p>`
    );
});
test("can undo add link to inline image + text", async () => {
    const { editor, el } = await setupEditor(`<p>ab[cd<img src="${base64Img}">ef]g</p>`);
    await waitFor(".o-we-toolbar");
    await click(".o-we-toolbar .fa-link");
    await contains(".o-we-linkpopover input.o_we_href_input_link", { timeout: 1500 }).edit(
        "http://test.test/"
    );
    expect(cleanLinkArtifacts(getContent(el))).toBe(
        `<p>ab<a href="http://test.test/">cd<img src="${base64Img}">ef[]</a>g</p>`
    );
    undo(editor);
    await animationFrame();
    expect(cleanLinkArtifacts(getContent(el))).toBe(`<p>ab[cd<img src="${base64Img}">ef]g</p>`);
});
test("can remove link from an inline image", async () => {
    const { el } = await setupEditor(
        `<p>ab<a href="http://test.test/">cd<img src="${base64Img}">ef</a>g</p>`
    );
    await click("img");
    await waitFor(".o-we-toolbar");
    expect("button[name='unlink']").toHaveCount(1);
    await click("button[name='unlink']");
    await animationFrame();
    expect(cleanLinkArtifacts(getContent(el))).toBe(
        `<p>ab<a href="http://test.test/">cd[</a><img src="${base64Img}"><a href="http://test.test/">]ef</a>g</p>`
    );
    await expectElementCount(".o-we-linkpopover", 0);
});
test("can remove link from a selection of an inline image + text", async () => {
    const { el } = await setupEditor(
        `<p>ab<a href="http://test.test/">c[d<img src="${base64Img}">e]f</a>g</p>`
    );
    await waitFor(".o-we-toolbar");
    await click(".o-we-toolbar .fa-unlink");
    expect(cleanLinkArtifacts(getContent(el))).toBe(
        `<p>ab<a href="http://test.test/">c</a>[d<img src="${base64Img}">e]<a href="http://test.test/">f</a>g</p>`
    );
});
test("can remove link from a selection (ltr) with multiple inline images", async () => {
    const { el } = await setupEditor(
        `<p>ab<a href="http://test.test/">c[d<img src="${base64Img}">e<img src="${base64Img}">f]g</a>h</p>`
    );
    await waitFor(".o-we-toolbar");
    await click(".o-we-toolbar .fa-unlink");
    expect(cleanLinkArtifacts(getContent(el))).toBe(
        `<p>ab<a href="http://test.test/">c</a>[d<img src="${base64Img}">e<img src="${base64Img}">f]<a href="http://test.test/">g</a>h</p>`
    );
});
test("can remove link from a selection (rtl) with multiple inline images", async () => {
    const { el } = await setupEditor(
        `<p>ab<a href="http://test.test/">c]d<img src="${base64Img}">e<img src="${base64Img}">f[g</a>h</p>`
    );
    await waitFor(".o-we-toolbar");
    await click(".o-we-toolbar .fa-unlink");
    expect(cleanLinkArtifacts(getContent(el))).toBe(
        `<p>ab<a href="http://test.test/">c</a>]d<img src="${base64Img}">e<img src="${base64Img}">f[<a href="http://test.test/">g</a>h</p>`
    );
});
test("can remove link from a selection (ltr) with multiple inline images acrossing different links", async () => {
    const { el } = await setupEditor(
        `<p>ab<a href="http://test.test/">c[d<img src="${base64Img}">e</a>xx<a href="http://test.test/">f<img src="${base64Img}">g]h</a>i</p>`
    );
    await waitFor(".o-we-toolbar");
    await click(".o-we-toolbar .fa-unlink");
    expect(cleanLinkArtifacts(getContent(el))).toBe(
        `<p>ab<a href="http://test.test/">c</a>[d<img src="${base64Img}">exxf<img src="${base64Img}">g]<a href="http://test.test/">h</a>i</p>`
    );
});
test("can remove link from a selection (rtl) with multiple inline images acrossing different links", async () => {
    const { el } = await setupEditor(
        `<p>ab<a href="#">c]d<img src="${base64Img}">e</a>xx<a href="#">f<img src="${base64Img}">g[h</a>i</p>`
    );
    await waitFor(".o-we-toolbar");
    await click(".o-we-toolbar .fa-unlink");
    expect(cleanLinkArtifacts(getContent(el))).toBe(
        `<p>ab<a href="#">c</a>]d<img src="${base64Img}">exxf<img src="${base64Img}">g[<a href="#">h</a>i</p>`
    );
});
test("link element should be removed and popover should close when image is deleted from a image link", async () => {
    const { editor, el } = await setupEditor(
        `<p>ab<a href="http://test.test/"><img src="${base64Img}"></a>c[]</p>`
    );
    await click("img");
    await waitFor(".o-we-toolbar");
    await waitFor(".o-we-linkpopover");

    execCommand(editor, "deleteImage");
    await waitForNone(".o-we-linkpopover", { timeout: 1500 });

    expect(cleanLinkArtifacts(getContent(el))).toBe(`<p>ab[]c</p>`);
});
test("selecting text and a image with link should not extend the link element", async () => {
    const { el } = await setupEditor(
        `<p>ab<a href="http://test.test/">cd<img src="${base64Img}">ef</a>g</p>`
    );
    setContent(el, `<p>ab<a href="http://test.test/">c]d<img src="${base64Img}">e[f</a>g</p>`);
    await waitFor(".o-we-linkpopover", { timeout: 1500 });
    await waitFor(".o-we-toolbar");
    setContent(el, `<p>a]b<a href="http://test.test/">cd<img src="${base64Img}">e[f</a>g</p>`);
    await waitForNone(".o-we-linkpopover", { timeout: 1500 });
    expect(cleanLinkArtifacts(getContent(el))).toBe(
        `<p>a]b<a href="http://test.test/">cd<img src="${base64Img}">e[f</a>g</p>`
    );
});
test("when clearing link URL for an image and clicking outside does not change href", async () => {
    const { el } = await setupEditor(
        `<p><a href="http://test.test/">[<img src="${base64Img}">]</a></p>`
    );
    await waitFor(".o-we-linkpopover", { timeout: 1500 });
    await click(".o_we_edit_link");
    await waitFor(".o_we_href_input_link");
    await contains(".o-we-linkpopover input.o_we_href_input_link").clear();
    await click(el);
    // Simulate click outside
    const pNode = queryOne("p");
    setSelection({
        anchorNode: pNode,
        anchorOffset: 0,
        focusNode: pNode,
        focusOffset: 0,
    });
    await tick(); // wait for selection change.
    await waitForNone(".o-we-linkpopover", { timeout: 1500 });
    expect(getContent(el)).toBe(
        `<p>[]<a href="http://test.test/"><img src="${base64Img}"></a></p>`
    );
});
// TODO: need to check with AGE
test.todo("popover should not open for not editable image", async () => {
    await setupEditor(`<a href="#"><img src="${base64Img}" contenteditable="false"></a>`);
    await click("img");
    await animationFrame();
    await expectElementCount(".o-we-linkpopover", 0);
});
test("label field should be hidden if <a> content is not text only", async () => {
    await setupEditor(`<p><a href="http://test.com/"><img src="${base64Img}">te[]xt</a></p>`);
    await expectElementCount(".o-we-linkpopover", 1);
    // open edit mode and check if label input is hidden
    await click(".o_we_edit_link");
    await waitFor(".o_we_href_input_link", { timeout: 1500 });
    expect(".o_we_label_link").not.toBeVisible();
    expect(".o_we_href_input_link").toHaveValue("http://test.com/");
});
test("when you open image link popover, url input should be focus by default", async () => {
    const { el } = await setupEditor(`<p>[<img src="${base64Img}">]</p>`);
    await waitFor(".o-we-toolbar");
    await click(".o-we-toolbar .fa-link");
    await waitFor(".o-we-linkpopover", { timeout: 1500 });
    expect(".o-we-linkpopover input.o_we_href_input_link").toBeFocused();

    await press("escape");
    await expectElementCount(".o-we-linkpopover", 0);
    expect(getContent(el)).toBe(`<p>[<img src="${base64Img}">]</p>`);
});
