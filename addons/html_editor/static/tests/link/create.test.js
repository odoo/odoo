import { describe, expect, test } from "@odoo/hoot";
import { click, press, fill, queryFirst, queryOne, queryText, waitFor } from "@odoo/hoot-dom";
import { animationFrame, tick } from "@odoo/hoot-mock";
import { contains } from "@web/../tests/web_test_helpers";
import { setupEditor } from "../_helpers/editor";
import { cleanLinkArtifacts } from "../_helpers/format";
import { getContent, setSelection } from "../_helpers/selection";
import { expectElementCount } from "../_helpers/ui_expectations";
import { insertLineBreak, insertText, splitBlock, undo } from "../_helpers/user_actions";

describe("link creation by powerbox", () => {
    test("click on link command in powerbox should not (yet) create a link element and open the linkpopover", async () => {
        const { editor, el } = await setupEditor("<p>ab[]</p>");
        await insertText(editor, "/link");
        await animationFrame();
        expect(".active .o-we-command-name").toHaveText("Link");

        await click(".o-we-command-name:first");
        expect(cleanLinkArtifacts(getContent(el))).toBe("<p>ab[]</p>");
        await expectElementCount(".o-we-linkpopover", 1);
        expect(".o-we-linkpopover input.o_we_label_link").toBeFocused({
            message: "should focus label input by default, when we don't have a label",
        });
    });

    test("when create a new link by powerbox and not input anything, the link should be removed", async () => {
        const { editor, el } = await setupEditor("<p>ab[]</p>");
        await insertText(editor, "/link");
        await animationFrame();
        await click(".o-we-command-name:first");
        await expectElementCount(".o-we-linkpopover", 1);
        expect(cleanLinkArtifacts(getContent(el))).toBe("<p>ab</p>");
        // simulate click outside
        const pNode = queryOne("p");
        setSelection({
            anchorNode: pNode,
            anchorOffset: 0,
            focusNode: pNode,
            focusOffset: 0,
        });
        await animationFrame();
        expect(cleanLinkArtifacts(getContent(el))).toBe("<p>[]ab</p>");
    });
    test("when create a new link by powerbox and not input anything, the apply link button should be disable", async () => {
        const { editor, el } = await setupEditor("<p>ab[]</p>");
        await insertText(editor, "/link");
        await animationFrame();
        await click(".o-we-command-name:first");
        await waitFor(".o-we-linkpopover");
        await expectElementCount(".o-we-linkpopover", 1);
        expect(cleanLinkArtifacts(getContent(el))).toBe("<p>ab</p>");
        expect(".o_we_apply_link").toHaveAttribute("disabled");
    });
    test("when create a new link by powerbox and only input the URL, the link should be created with corrected https URL", async () => {
        const { editor, el } = await setupEditor("<p>ab[]</p>");
        await insertText(editor, "/link");
        await animationFrame();
        await click(".o-we-command-name:first");

        await contains(".o-we-linkpopover input.o_we_href_input_link").fill("test.com");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>ab<a href="https://test.com">test.com[]</a></p>'
        );
    });
    test("Should be able to insert link on empty p", async () => {
        const { editor, el } = await setupEditor("<p>[]<br></p>");
        await insertText(editor, "/link");
        await animationFrame();
        await click(".o-we-command-name:first");

        await contains(".o-we-linkpopover input.o_we_href_input_link").fill("http://test.test/");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.test/">http://test.test/[]</a></p>'
        );
    });
    test("Should be able to insert button on empty p", async () => {
        const { editor, el } = await setupEditor("<p>[]<br></p>");
        await insertText(editor, "/button");
        await animationFrame();
        await click(".o-we-command-name:first");

        await contains(".o-we-linkpopover input.o_we_href_input_link").fill("http://test.test/");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.test/" class="btn btn-primary">http://test.test/[]</a></p>'
        );
    });
    test("Should keep http protocol on valid http url", async () => {
        const { editor, el } = await setupEditor("<p>[]<br></p>");
        await insertText(editor, "/link");
        await animationFrame();
        await click(".o-we-command-name:first");

        await contains(".o-we-linkpopover input.o_we_href_input_link").fill("http://google.com");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://google.com">http://google.com[]</a></p>'
        );
    });
    test("should insert a link and preserve spacing", async () => {
        const { editor, el } = await setupEditor("<p>a []&nbsp;&nbsp;b</p>");
        await insertText(editor, "/link");
        await animationFrame();
        await click(".o-we-command-name:first");
        await contains(".o-we-linkpopover input.o_we_label_link").fill("link");
        await contains(".o-we-linkpopover input.o_we_href_input_link").fill("http://test.test/");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>a <a href="http://test.test/">link[]</a>&nbsp;&nbsp;b</p>'
        );
    });
    test("should insert a link then create a new <p>", async () => {
        const { editor, el } = await setupEditor("<p>ab[]</p>");
        await insertText(editor, "/link");
        await animationFrame();
        await click(".o-we-command-name:first");
        await contains(".o-we-linkpopover input.o_we_label_link").fill("link");
        await contains(".o-we-linkpopover input.o_we_href_input_link").fill("http://test.test/");
        // press("Enter");
        splitBlock(editor);
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            `<p>ab<a href="http://test.test/">link</a></p><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`
        );
    });
    test("should insert a link then create a new <p>, and another character", async () => {
        const { editor, el } = await setupEditor("<p>a[]b</p>");
        await insertText(editor, "/link");
        await animationFrame();
        await click(".o-we-command-name:first");
        await contains(".o-we-linkpopover input.o_we_label_link").fill("link");
        await contains(".o-we-linkpopover input.o_we_href_input_link").fill("http://test.test/");
        // press("Enter");
        splitBlock(editor);
        await insertText(editor, "D");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>a<a href="http://test.test/">link</a></p><p>D[]b</p>'
        );
    });
    test("should insert a link then insert a <br>", async () => {
        const { editor, el } = await setupEditor("<p>a[]b</p>");
        await insertText(editor, "/link");
        await animationFrame();
        await click(".o-we-command-name:first");
        await contains(".o-we-linkpopover input.o_we_label_link").fill("link");
        await contains(".o-we-linkpopover input.o_we_href_input_link").fill("http://test.test/");
        // press("Enter");
        insertLineBreak(editor);
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>a<a href="http://test.test/">link</a><br>[]b</p>'
        );
    });
    test("should insert a link then insert a <br> and another character", async () => {
        const { editor, el } = await setupEditor("<p>a[]b</p>");
        await insertText(editor, "/link");
        await animationFrame();
        await click(".o-we-command-name:first");
        await contains(".o-we-linkpopover input.o_we_label_link").fill("link");
        await contains(".o-we-linkpopover input.o_we_href_input_link").fill("http://test.test/");
        // press("Enter");
        insertLineBreak(editor);
        await insertText(editor, "D");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>a<a href="http://test.test/">link</a><br>D[]b</p>'
        );
    });
});

describe("link creation by toolbar", () => {
    test("should convert all selected text to link", async () => {
        const { el } = await setupEditor("<p>[Hello]</p>");
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-link");
        await contains(".o-we-linkpopover input.o_we_href_input_link", { timeout: 1500 }).edit(
            "http://test.test/"
        );
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.test/">Hello[]</a></p>'
        );
    });
    test("discard should close the popover (in iframe)", async () => {
        await setupEditor("<p>[Hello]</p>", { props: { iframe: true } });
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-link");
        await waitFor(".o-we-linkpopover", { timeout: 1500 });
        await click(".o_we_discard_link");
        await animationFrame();
        expect(".o-we-linkpopover").toHaveCount(0);
    });
    test("should convert valid url to https link", async () => {
        const { el } = await setupEditor("<p>[Hello]</p>");
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-link");
        await contains(".o-we-linkpopover input.o_we_href_input_link", { timeout: 1500 }).edit(
            "google.com"
        );
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="https://google.com">Hello[]</a></p>'
        );
    });
    test("should convert valid http url to http link", async () => {
        const { el } = await setupEditor("<p>[Hello]</p>");
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-link");
        await contains(".o-we-linkpopover input.o_we_href_input_link", { timeout: 1500 }).edit(
            "http://google.com"
        );
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://google.com">Hello[]</a></p>'
        );
    });
    test("should convert all selected text to link and keep style except color", async () => {
        const { el } = await setupEditor(
            '<p>Hello this is [a <b>new</b> <u>link</u> <span style="color:red">keeping</span> style]!</p>'
        );
        await waitFor(".o-we-toolbar");
        click(".o-we-toolbar .fa-link");
        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("http://test.test/");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>Hello this is <a href="http://test.test/">a <b>new</b> <u>link</u> keeping style[]</a>!</p>'
        );
    });
    test("should convert all selected text to link and keep style except bgclor", async () => {
        const { el } = await setupEditor(
            '<p>Hello this is [a <b>new</b> <u>link</u> <span style="background-color:red">keeping</span> style]!</p>'
        );
        await waitFor(".o-we-toolbar");
        click(".o-we-toolbar .fa-link");
        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("http://test.test/");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>Hello this is <a href="http://test.test/">a <b>new</b> <u>link</u> keeping style[]</a>!</p>'
        );
    });
    test("should convert all selected text to link and keep style except color (2)", async () => {
        const { el } = await setupEditor(
            '<p>Hello this is a <b>ne[w</b> <u>link</u> <span style="color:red">keep]ing</span> style!</p>'
        );
        await waitFor(".o-we-toolbar");
        click(".o-we-toolbar .fa-link");
        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("http://test.test/");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>Hello this is a <b>ne</b><a href="http://test.test/"><b>w</b> <u>link</u> keep[]</a><span style="color:red">ing</span> style!</p>'
        );
    });
    test("should set the link on two existing characters", async () => {
        const { el } = await setupEditor("<p>H[el]lo</p>");
        await waitFor(".o-we-toolbar");
        // link button should be enabled
        expect('.o-we-toolbar button[name="link"]').not.toHaveClass("disabled");
        expect('.o-we-toolbar button[name="link"]').not.toHaveAttribute("disabled");
        await click(".o-we-toolbar .fa-link");
        await contains(".o-we-linkpopover input.o_we_href_input_link", { timeout: 1500 }).edit(
            "http://test.test/"
        );
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>H<a href="http://test.test/">el[]</a>lo</p>'
        );
    });
    test("should not allow to create a link if selection span multiple block", async () => {
        const { el } = await setupEditor("<p>H[ello</p><p>wor]ld</p>");
        await waitFor(".o-we-toolbar");
        // link button should be disabled
        expect('.o-we-toolbar button[name="link"]').toHaveClass("disabled");
        expect('.o-we-toolbar button[name="link"]').toHaveAttribute("disabled");
        await click('.o-we-toolbar button[name="link"]');
        expect(getContent(el)).toBe("<p>H[ello</p><p>wor]ld</p>");
    });
    test("when you open link popover, url input should be focus by default", async () => {
        const { el } = await setupEditor("<p>[Hello]</p>");
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-link");
        await waitFor(".o-we-linkpopover", { timeout: 1500 });
        expect(".o-we-linkpopover input.o_we_href_input_link").toBeFocused();

        await fill("test.com");
        await waitFor(".o_we_apply_link:not([disabled])");
        await click(".o_we_apply_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="https://test.com">Hello[]</a></p>'
        );
    });

    test("should be correctly unlink/link", async () => {
        const { el } = await setupEditor('<p>aaaa[b<a href="http://test.com/">cd</a>e]f</p>');
        await waitFor(".o-we-toolbar");

        await click(".o-we-toolbar .fa-unlink");
        await tick();
        expect(cleanLinkArtifacts(getContent(el))).toBe("<p>aaaa[bcde]f</p>");
        const pNode = queryOne("p");
        setSelection({
            anchorNode: pNode.childNodes[1],
            anchorOffset: 1,
            focusNode: pNode.childNodes[0],
            focusOffset: 3,
        });
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-link");
        await contains(".o-we-linkpopover input.o_we_href_input_link", { timeout: 1500 }).edit(
            "http://test.test/"
        );
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>aaa<a href="http://test.test/">ab[]</a>cdef</p>'
        );
    });
    test("should remove link when click away without inputting url", async () => {
        const { el } = await setupEditor("<p>H[el]lo</p>");
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-link");
        await waitFor(".o-we-linkpopover", { timeout: 1500 });
        const pNode = queryOne("p");
        setSelection({
            anchorNode: pNode,
            anchorOffset: 0,
            focusNode: pNode,
            focusOffset: 0,
        });
        await tick();
        expect(cleanLinkArtifacts(getContent(el))).toBe("<p>[]Hello</p>");
    });
    test("when selection includes partially a link and click the link icon in toolbar, the link should be extended", async () => {
        const { el } = await setupEditor('<p>a[b<a href="http://test.com/">c]d</a>ef</p>');
        await waitFor(".o-we-toolbar");

        await click(".o-we-toolbar .fa-link");
        await expectElementCount(".o-we-linkpopover", 1);
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>a<a href="http://test.com/">bcd[]</a>ef</p>'
        );
    });
    test("when selection includes a link and click the link icon in toolbar, the link should be extended", async () => {
        const { el } = await setupEditor('<p>a[b<a href="http://test.com/">cd</a>e]f</p>');
        await waitFor(".o-we-toolbar");

        await click(".o-we-toolbar .fa-link");
        await expectElementCount(".o-we-linkpopover", 1);
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>a<a href="http://test.com/">bcde[]</a>f</p>'
        );
    });
    test("when create a link on selection which doesn't include a link, it should create a new one", async () => {
        await setupEditor('<p><strong>abc<a href="http://test.com/">de</a>te[st</strong> m]e</p>');
        await waitFor(".o-we-toolbar");

        await click(".o-we-toolbar .fa-link");
        await waitFor(".o-we-linkpopover", { timeout: 1500 });
        expect(".o_we_label_link").toHaveValue("st m");
        expect(".o_we_href_input_link").toHaveValue("");
    });
    test("create a link and undo it (1)", async () => {
        const { el, editor } = await setupEditor("<p>[Hello]</p>");
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-link");
        // not validated link shouldn't affect the DOM yet
        expect(cleanLinkArtifacts(getContent(el))).toBe("<p>[Hello]</p>");
        await contains(".o-we-linkpopover input.o_we_href_input_link", { timeout: 1500 }).edit(
            "http://test.test/"
        );
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.test/">Hello[]</a></p>'
        );

        undo(editor);
        expect(cleanLinkArtifacts(getContent(el))).toBe("<p>[Hello]</p>");
    });
    test("create a link and undo it (2)", async () => {
        const { el, editor } = await setupEditor("<p><b>[Hello]</b></p>");
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-link");
        // not validated link shouldn't affect the DOM yet
        expect(cleanLinkArtifacts(getContent(el))).toBe("<p><b>[Hello]</b></p>");
        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("http://test.test/");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><b><a href="http://test.test/">Hello[]</a></b></p>'
        );
        undo(editor);
        expect(cleanLinkArtifacts(getContent(el))).toBe("<p><b>[Hello]</b></p>");
    });
    test("extend a link on selection and undo it", async () => {
        const { el, editor } = await setupEditor(
            `<p>[<a href="https://www.test.com">Hello</a> my friend]</p>`
        );
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-link");
        await waitFor(".o-we-linkpopover", { timeout: 1500 });
        expect(queryFirst(".o-we-linkpopover a").href).toBe("https://www.test.com/");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            `<p><a href="https://www.test.com">Hello my friend[]</a></p>`
        );

        undo(editor);
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            `<p>[<a href="https://www.test.com">Hello</a> my friend]</p>`
        );
    });
});

describe("link creation by shortcut", () => {
    test("create link shortcut should be at the first", async () => {
        const { editor } = await setupEditor(`<p>[]</p>`);
        editor.services.command.add("A test command", () => {}, {
            hotkey: "alt+k",
            category: "app",
        });

        await press(["ctrl", "k"]);
        await animationFrame();
        expect(queryText(".o_command_name:first")).toBe("Create link");
    });
    test.tags("desktop");
    test("create a link with shortcut", async () => {
        const { el } = await setupEditor(`<p>[]<br></p>`);
        // open odoo command bar
        await press(["ctrl", "k"]);
        await waitFor('.o_command span[title="Create link"]');
        // open link tool
        await click(".o_command_name:first");
        await waitFor(".o-we-linkpopover");
        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("test.com");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="https://test.com">test.com[]</a></p>'
        );
    });
    test.tags("desktop");
    test("should be able to create link with ctrl+k and ctrl+k", async () => {
        const { el } = await setupEditor(`<p>[]<br></p>`);
        // Open odoo global command bar
        await press(["ctrl", "k"]);
        await waitFor('.o_command span[title="Create link"]');
        // Choose the "create link" command to create a link in the editor
        await press(["ctrl", "k"]);
        await waitFor(".o-we-linkpopover");
        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("test.com");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="https://test.com">test.com[]</a></p>'
        );
    });
    test("should be able to create link with ctrl+k , and should make link on two existing characters", async () => {
        const { el } = await setupEditor(`<p>H[el]lo</p>`);

        await press(["ctrl", "k"]);
        await animationFrame();
        await press(["ctrl", "k"]);
        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("test.com");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>H<a href="https://test.com">el[]</a>lo</p>'
        );
    });
    test("Press enter to apply when create a link", async () => {
        const { el } = await setupEditor(`<p><a>li[]nk</a></p>`);

        await contains(".o-we-linkpopover input.o_we_href_input_link").fill("test.com");
        await press("Enter");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="https://test.com">li[]nk</a></p>'
        );
    });
});
