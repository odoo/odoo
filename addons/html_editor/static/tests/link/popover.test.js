import { describe, expect, test } from "@odoo/hoot";
import {
    click,
    fill,
    press,
    queryAllTexts,
    queryFirst,
    queryOne,
    queryText,
    select,
    waitFor,
    waitForNone,
} from "@odoo/hoot-dom";
import { animationFrame, tick } from "@odoo/hoot-mock";
import { markup } from "@odoo/owl";
import { contains, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupEditor } from "../_helpers/editor";
import { cleanLinkArtifacts } from "../_helpers/format";
import { getContent, setContent, setSelection } from "../_helpers/selection";
import { insertLineBreak, insertText, splitBlock, undo } from "../_helpers/user_actions";
import { execCommand } from "../_helpers/userCommands";

const base64Img =
    "data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAAUA\n        AAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO\n            9TXL0Y4OHwAAAABJRU5ErkJggg==";

describe("should open a popover", () => {
    test("should open a popover when the selection is inside a link and close outside of a link", async () => {
        const { el } = await setupEditor("<p>this is a <a>link</a></p>");
        expect(".o-we-linkpopover").toHaveCount(0);
        // selection inside a link
        setContent(el, "<p>this is a <a>li[]nk</a></p>");
        await waitFor(".o-we-linkpopover");
        expect(".o-we-linkpopover").toHaveCount(1);
        // selection outside a link
        setContent(el, "<p>this []is a <a>link</a></p>");
        await waitForNone(".o-we-linkpopover", { timeout: 1500 });
        expect(".o-we-linkpopover").toHaveCount(0);
    });
    test("link popover should have input field for href when the link doesn't have href", async () => {
        await setupEditor("<p>this is a <a>li[]nk</a></p>");
        await waitFor(".o-we-linkpopover");
        expect(".o-we-linkpopover").toHaveCount(1);
        expect(".o_we_label_link").toHaveValue("link");
        expect(".o_we_href_input_link").toHaveValue("");
    });
    test("link popover should have buttons for link operation when the link has href", async () => {
        await setupEditor('<p>this is a <a href="test.com">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        expect(".o-we-linkpopover").toHaveCount(1);
        expect(".o_we_copy_link").toHaveCount(1);
        expect(".o_we_edit_link").toHaveCount(1);
        expect(".o_we_remove_link").toHaveCount(1);
    });
    test("link popover should not repositioned when clicking in the input field", async () => {
        await setupEditor("<p>this is a <a>li[]nk</a></p>");
        await waitFor(".o_we_href_input_link");
        const style = queryOne(".o-we-linkpopover").parentElement.style.cssText;
        queryOne(".o_we_href_input_link").focus();
        await animationFrame();
        expect(queryOne(".o-we-linkpopover").parentElement).toHaveAttribute("style", style);
    });
    test("link popover should close when click on editable without url", async () => {
        const { el } = await setupEditor(`<p>[<img src="${base64Img}">]</p>`);
        await animationFrame();
        // we create a link without href on img
        await click("button[name='link']");
        await waitFor(".o_we_href_input_link");
        // we put selection out of editor
        setSelection({
            anchorNode: document.body,
            anchorOffset: 0,
        });
        await animationFrame();
        // Restore the selection in the editor. Setting the selection after the image
        // will place it inside the `<a>` tag if not removed, causing a traceback.
        setSelection({
            anchorNode: el.querySelector("img").parentElement,
            anchorOffset: 1,
        });
        await animationFrame();
        expect(".o-we-linkpopover").toHaveCount(0);
    });
});

describe("popover should switch UI depending on editing state", () => {
    test("after clicking on edit button, the popover should switch to editing mode", async () => {
        await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await waitFor(".o_we_href_input_link");
        expect(".o_we_label_link").toHaveValue("link");
        expect(".o_we_href_input_link").toHaveValue("http://test.com/");
    });
    test("after clicking on apply button, the selection should be restored", async () => {
        const { el } = await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await waitFor(".o_we_href_input_link");
        await click(".o_we_href_input_link");
        await click(".o_we_apply_link");
        await waitFor(".o_we_edit_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="http://test.com/">li[]nk</a></p>'
        );
    });
    test("after editing the URL and clicking on apply button, the selection should be restored", async () => {
        const { el } = await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await waitFor(".o_we_href_input_link");
        // This changes the selection to outside the editor.
        await click(".o_we_href_input_link");
        await tick();
        await press("a");
        await click(".o_we_apply_link");
        await waitFor(".o_we_edit_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="http://test.com/a">li[]nk</a></p>'
        );
    });
    test("after clicking on apply button, the popover should be with the non editing mode, e.g. with three buttons", async () => {
        await setupEditor("<p>this is a <a>li[]nk</a></p>");
        await waitFor(".o-we-linkpopover");
        await click(".o_we_href_input_link");
        await click(".o_we_apply_link");
        await waitFor(".o_we_edit_link");
        expect(".o-we-linkpopover").toHaveCount(1);
        expect(".o_we_copy_link").toHaveCount(1);
        expect(".o_we_edit_link").toHaveCount(1);
        expect(".o_we_remove_link").toHaveCount(1);
    });
});

describe("popover should edit,copy,remove the link", () => {
    test("after apply url on a link without href, the link element should be updated", async () => {
        const { el } = await setupEditor("<p>this is a <a>li[]nk</a></p>");

        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("http://test.com/");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="http://test.com/">li[]nk</a></p>'
        );
    });
    test("after clicking on remove button, the link element should be unwrapped", async () => {
        const { el } = await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_remove_link");
        await waitForNone(".o-we-linkpopover", { timeout: 1500 });
        expect(getContent(el)).toBe("<p>this is a li[]nk</p>");
    });
    test("after edit the label, the text of the link should be updated", async () => {
        const { el } = await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");

        await contains(".o-we-linkpopover input.o_we_label_link").fill("new");
        await click(".o_we_apply_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="http://test.com/">linknew[]</a></p>'
        );
    });
    test("when the label is empty, it should be set as the URL", async () => {
        const { el } = await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await waitFor(".o_we_apply_link");

        await contains(".o-we-linkpopover input.o_we_label_link").clear();
        await click(".o_we_apply_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="http://test.com/">http://test.com/[]</a></p>'
        );
    });
    test("after clicking on copy button, the url should be copied to clipboard", async () => {
        await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_copy_link");
        await waitFor(".o_notification_bar.bg-success");
        const notifications = queryAllTexts(".o_notification_body");
        expect(notifications).toInclude("Link copied to clipboard.");
        await animationFrame();
        expect(".o-we-linkpopover").toHaveCount(0);
        await expect(navigator.clipboard.readText()).resolves.toBe("http://test.com/");
    });
    test("when edit a link's label and URL to '', the link should be removed", async () => {
        const { el } = await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");

        await contains(".o-we-linkpopover input.o_we_label_link").clear();
        await contains(".o-we-linkpopover input.o_we_href_input_link").clear();
        expect(getContent(el)).toBe("<p>this is a&nbsp;[]</p>");
    });
});

describe("Incorrect URL should be corrected", () => {
    test("when edit a link's URL to 'test.com', the link's URL should be corrected", async () => {
        const { el } = await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");

        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("newtest.com");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="http://newtest.com">li[]nk</a></p>'
        );
    });
    test("when a link's URL is an email, the link's URL should start with mailto:", async () => {
        const { el } = await setupEditor("<p>this is a <a>li[]nk</a></p>");

        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("test@test.com");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="mailto:test@test.com">li[]nk</a></p>'
        );
    });
    test("when a link's URL is an phonenumber, the link's URL should start with tel:", async () => {
        const { el } = await setupEditor("<p>this is a <a>li[]nk</a></p>");

        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("+1234567890");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="tel:+1234567890">li[]nk</a></p>'
        );
    });
});

describe("Link creation", () => {
    describe("Creation by space", () => {
        test("typing valid URL + space should convert to link", async () => {
            const { editor, el } = await setupEditor("<p>[]</p>");
            await insertText(editor, "http://google.co.in");
            await insertText(editor, " ");
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                '<p><a href="http://google.co.in">http://google.co.in</a>&nbsp;[]</p>'
            );
        });
        test("typing invalid URL + space should not convert to link", async () => {
            const { editor, el } = await setupEditor("<p>[]</p>");
            await insertText(editor, "www.odoo");
            await insertText(editor, " ");
            expect(cleanLinkArtifacts(getContent(el))).toBe("<p>www.odoo []</p>");
        });
    });
    describe("Creation by powerbox", () => {
        test("click on link command in powerbox should create a link element and open the linkpopover", async () => {
            const { editor, el } = await setupEditor("<p>ab[]</p>");
            await insertText(editor, "/link");
            await animationFrame();
            expect(".active .o-we-command-name").toHaveText("Link");

            await click(".o-we-command-name:first");
            expect(cleanLinkArtifacts(getContent(el))).toBe("<p>ab<a>[]</a></p>");
            await waitFor(".o-we-linkpopover");
            expect(".o-we-linkpopover").toHaveCount(1);
            expect(".o-we-linkpopover input.o_we_label_link").toBeFocused({
                message: "should focus label input by default, when we don't have a label",
            });
        });

        test("creating link in an empty block using link command should not contain trailing br", async () => {
            const { editor, el } = await setupEditor("<p>[]<br></p>");
            await insertText(editor, "/link");
            await animationFrame();
            expect(".active .o-we-command-name").toHaveText("Link");
            await click(".o-we-command-name:first");
            await contains(".o-we-linkpopover input.o_we_href_input_link").fill("test.com");
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                '<p><a href="http://test.com">test.com[]</a></p>'
            );
        });

        test("when create a new link by powerbox and not input anything, the link should be removed", async () => {
            const { editor, el } = await setupEditor("<p>ab[]</p>");
            await insertText(editor, "/link");
            await animationFrame();
            await click(".o-we-command-name:first");
            await waitFor(".o-we-linkpopover");
            expect(".o-we-linkpopover").toHaveCount(1);
            expect(cleanLinkArtifacts(getContent(el))).toBe("<p>ab<a></a></p>");

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
        test("when create a new link by powerbox and only input the URL, the link should be created with corrected URL", async () => {
            const { editor, el } = await setupEditor("<p>ab[]</p>");
            await insertText(editor, "/link");
            await animationFrame();
            await click(".o-we-command-name:first");

            await contains(".o-we-linkpopover input.o_we_href_input_link").fill("test.com");
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                '<p>ab<a href="http://test.com">test.com[]</a></p>'
            );
        });
        test("Should be able to insert link on empty p", async () => {
            const { editor, el } = await setupEditor("<p>[]</p>");
            await insertText(editor, "/link");
            await animationFrame();
            await click(".o-we-command-name:first");

            await contains(".o-we-linkpopover input.o_we_href_input_link").fill("#");
            expect(cleanLinkArtifacts(getContent(el))).toBe('<p><a href="#">#[]</a></p>');
        });
        test("Should be able to insert button on empty p", async () => {
            const { editor, el } = await setupEditor("<p>[]</p>");
            await insertText(editor, "/button");
            await animationFrame();
            await click(".o-we-command-name:first");

            await contains(".o-we-linkpopover input.o_we_href_input_link").fill("#");
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                '<p><a class="btn btn-primary" href="#">#[]</a></p>'
            );
        });
        test("should insert a link and preserve spacing", async () => {
            const { editor, el } = await setupEditor("<p>a []&nbsp;&nbsp;b</p>");
            await insertText(editor, "/link");
            await animationFrame();
            await click(".o-we-command-name:first");
            await contains(".o-we-linkpopover input.o_we_label_link").fill("link");
            await contains(".o-we-linkpopover input.o_we_href_input_link").fill("#");
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                '<p>a <a href="#">link[]</a>&nbsp;&nbsp;b</p>'
            );
        });
        test("should insert a link then create a new <p>", async () => {
            const { editor, el } = await setupEditor("<p>ab[]</p>");
            await insertText(editor, "/link");
            await animationFrame();
            await click(".o-we-command-name:first");
            await contains(".o-we-linkpopover input.o_we_label_link").fill("link");
            await contains(".o-we-linkpopover input.o_we_href_input_link").fill("#");
            // press("Enter");
            splitBlock(editor);
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                `<p>ab<a href="#">link</a></p><p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>`
            );
        });
        test("should insert a link then create a new <p>, and another character", async () => {
            const { editor, el } = await setupEditor("<p>a[]b</p>");
            await insertText(editor, "/link");
            await animationFrame();
            await click(".o-we-command-name:first");
            await contains(".o-we-linkpopover input.o_we_label_link").fill("link");
            await contains(".o-we-linkpopover input.o_we_href_input_link").fill("#");
            // press("Enter");
            splitBlock(editor);
            await insertText(editor, "D");
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                '<p>a<a href="#">link</a></p><p>D[]b</p>'
            );
        });
        test("should insert a link then insert a <br>", async () => {
            const { editor, el } = await setupEditor("<p>a[]b</p>");
            await insertText(editor, "/link");
            await animationFrame();
            await click(".o-we-command-name:first");
            await contains(".o-we-linkpopover input.o_we_label_link").fill("link");
            await contains(".o-we-linkpopover input.o_we_href_input_link").fill("#");
            // press("Enter");
            insertLineBreak(editor);
            expect(cleanLinkArtifacts(getContent(el))).toBe('<p>a<a href="#">link</a><br>[]b</p>');
        });
        test("should insert a link then insert a <br> and another character", async () => {
            const { editor, el } = await setupEditor("<p>a[]b</p>");
            await insertText(editor, "/link");
            await animationFrame();
            await click(".o-we-command-name:first");
            await contains(".o-we-linkpopover input.o_we_label_link").fill("link");
            await contains(".o-we-linkpopover input.o_we_href_input_link").fill("#");
            // press("Enter");
            insertLineBreak(editor);
            await insertText(editor, "D");
            expect(cleanLinkArtifacts(getContent(el))).toBe('<p>a<a href="#">link</a><br>D[]b</p>');
        });
    });
    describe("Creation by toolbar", () => {
        test("should convert all selected text to link", async () => {
            const { el } = await setupEditor("<p>[Hello]</p>");
            await waitFor(".o-we-toolbar");
            await click(".o-we-toolbar .fa-link");
            await contains(".o-we-linkpopover input.o_we_href_input_link", { timeout: 1500 }).edit(
                "#"
            );
            expect(cleanLinkArtifacts(getContent(el))).toBe('<p><a href="#">Hello[]</a></p>');
        });
        test("should set the link on two existing characters", async () => {
            const { el } = await setupEditor("<p>H[el]lo</p>");
            await waitFor(".o-we-toolbar");
            await click(".o-we-toolbar .fa-link");
            await contains(".o-we-linkpopover input.o_we_href_input_link", { timeout: 1500 }).edit(
                "#"
            );
            expect(cleanLinkArtifacts(getContent(el))).toBe('<p>H<a href="#">el[]</a>lo</p>');
        });
        test("when you open link popover with a label, url input should be focus by default ", async () => {
            const { el } = await setupEditor("<p>[Hello]</p>");
            await waitFor(".o-we-toolbar");
            await click(".o-we-toolbar .fa-link");
            await waitFor(".o-we-linkpopover", { timeout: 1500 });
            expect(".o-we-linkpopover input.o_we_href_input_link").toBeFocused();

            await fill("test.com");
            await click(".o_we_apply_link");
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                '<p><a href="http://test.com">Hello[]</a></p>'
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
                "#"
            );
            expect(cleanLinkArtifacts(getContent(el))).toBe('<p>aaa<a href="#">ab[]</a>cdef</p>');
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
            await waitFor(".o-we-linkpopover", { timeout: 1500 });
            expect(".o-we-linkpopover").toHaveCount(1);
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                '<p>a<a href="http://test.com/">bcd[]</a>ef</p>'
            );
        });
        test("when selection includes a link and click the link icon in toolbar, the link should be extended", async () => {
            const { el } = await setupEditor('<p>a[b<a href="http://test.com/">cd</a>e]f</p>');
            await waitFor(".o-we-toolbar");

            await click(".o-we-toolbar .fa-link");
            await waitFor(".o-we-linkpopover", { timeout: 1500 });
            expect(".o-we-linkpopover").toHaveCount(1);
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                '<p>a<a href="http://test.com/">bcde[]</a>f</p>'
            );
        });
        test("when create a link on selection which doesn't include a link, it should create a new one", async () => {
            await setupEditor(
                '<p><strong>abc<a href="http://test.com/">de</a>te[st</strong> m]e</p>'
            );
            await waitFor(".o-we-toolbar");

            await click(".o-we-toolbar .fa-link");
            await waitFor(".o-we-linkpopover", { timeout: 1500 });
            expect(".o_we_label_link").toHaveValue("st m");
            expect(".o_we_href_input_link").toHaveValue("");
        });
        test("create a link and undo it", async () => {
            const { el, editor } = await setupEditor("<p>[Hello]</p>");
            await waitFor(".o-we-toolbar");
            await click(".o-we-toolbar .fa-link");
            await contains(".o-we-linkpopover input.o_we_href_input_link", { timeout: 1500 }).edit(
                "#"
            );
            expect(cleanLinkArtifacts(getContent(el))).toBe('<p><a href="#">Hello[]</a></p>');

            undo(editor);
            expect(cleanLinkArtifacts(getContent(el))).toBe("<p>[Hello]</p>");
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
});

describe.tags("desktop");
describe("Link formatting in the popover", () => {
    test("click on link, the link popover should load the current format correctly", async () => {
        await setupEditor(
            '<p><a href="http://test.com/" class="btn btn-outline-primary rounded-circle btn-lg">link2[]</a></p>'
        );
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        const linkPreviewEl = await waitFor("#link-preview");
        expect(linkPreviewEl).toHaveClass([
            "btn",
            "btn-outline-primary",
            "rounded-circle",
            "btn-lg",
        ]);
        expect(queryOne('select[name="link_type"]').selectedIndex).toBe(1);
        expect(queryOne('select[name="link_style_size"]').selectedIndex).toBe(2);
        expect(queryOne('select[name="link_style_shape"]').selectedIndex).toBe(3);
    });
    test("after changing the link format, the link preview should be updated", async () => {
        await setupEditor(
            '<p><a href="http://test.com/" class="btn btn-fill-secondary rounded-circle btn-sm">link2[]</a></p>'
        );
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");

        const linkPreviewEl = await waitFor("#link-preview");
        expect(linkPreviewEl).toHaveClass([
            "btn",
            "rounded-circle",
            "btn-fill-secondary",
            "btn-sm",
        ]);
        expect(queryOne('select[name="link_type"]').selectedIndex).toBe(2);
        expect(queryOne('select[name="link_style_size"]').selectedIndex).toBe(0);
        expect(queryOne('select[name="link_style_shape"]').selectedIndex).toBe(1);

        await click('select[name="link_type"');
        await select("primary");
        await click('select[name="link_style_size"');
        await select("lg");
        await click('select[name="link_style_shape"');
        await select("fill,rounded-circle");
        await animationFrame();
        expect(linkPreviewEl).toHaveClass(["btn", "btn-fill-primary", "rounded-circle", "btn-lg"]);
    });
    test("after applying the link format, the link's format should be updated", async () => {
        const { el } = await setupEditor('<p><a href="http://test.com/">link2[]</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await waitFor("#link-preview");
        expect(queryOne('select[name="link_type"]').selectedIndex).toBe(0);

        await click('select[name="link_type"');
        await select("secondary");
        await animationFrame();
        await click('select[name="link_style_shape"');
        await select("outline,rounded-circle");
        await animationFrame();

        const linkPreviewEl = queryOne("#link-preview");
        expect(linkPreviewEl).toHaveClass(["btn", "btn-outline-secondary", "rounded-circle"]);

        await click(".o_we_apply_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.com/" class="btn btn-outline-secondary rounded-circle">link2[]</a></p>'
        );
    });
    test("no preview of the link when the url is empty", async () => {
        await setupEditor("<p><a>link2[]</a></p>");
        await waitFor(".o-we-linkpopover");
        expect("#link-preview").toHaveCount(0);
    });
    test("when no label input, the link preview should have the content of the url", async () => {
        const { editor } = await setupEditor("<p>ab[]</p>");
        await insertText(editor, "/link");
        await animationFrame();
        await click(".o-we-command-name:first");
        await waitFor(".o-we-linkpopover");

        queryOne(".o_we_href_input_link").focus();
        for (const char of "newtest.com") {
            await press(char);
        }
        await animationFrame();
        const linkPreviewEl = queryOne("#link-preview");
        expect(linkPreviewEl).toHaveText("newtest.com");
    });
});

describe("shortcut", () => {
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
    test("create a link with shortcut", async () => {
        const { el } = await setupEditor(`<p>[]</p>`);

        await press(["ctrl", "k"]);
        await animationFrame();
        await click(".o_command_name:first");
        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("test.com");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.com">test.com[]</a></p>'
        );
    });
    test("should be able to create link with ctrl+k and ctrl+k", async () => {
        const { el } = await setupEditor(`<p>[]</p>`);

        await press(["ctrl", "k"]);
        await animationFrame();
        await press(["ctrl", "k"]);
        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("test.com");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.com">test.com[]</a></p>'
        );
    });
    test("should be able to create link with ctrl+k , and should make link on two existing characters", async () => {
        const { el } = await setupEditor(`<p>H[el]lo</p>`);

        await press(["ctrl", "k"]);
        await animationFrame();
        await press(["ctrl", "k"]);
        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("test.com");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>H<a href="http://test.com">el[]</a>lo</p>'
        );
    });
    test("Press enter to apply when create a link", async () => {
        const { el } = await setupEditor(`<p><a>li[]nk</a></p>`);

        await contains(".o-we-linkpopover input.o_we_href_input_link").fill("test.com");
        await press("Enter");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.com">li[]nk</a></p>'
        );
    });
});

describe("link preview", () => {
    test("test internal link preview", async () => {
        onRpc("/html_editor/link_preview_internal", () => {
            return {
                description: markup("Test description"),
                link_preview_name: "Task name | Project name",
            };
        });
        onRpc("/odoo/project/1/tasks/8", () => new Response("", { status: 200 }));
        const { editor, el } = await setupEditor(`<p>[]</p>`);
        await insertText(editor, "/link");
        await animationFrame();
        await click(".o-we-command-name:first");
        await contains(".o-we-linkpopover input.o_we_href_input_link").fill(
            window.location.origin + "/odoo/project/1/tasks/8"
        );
        await animationFrame();
        expect(".o_we_replace_title_btn").toHaveCount(1);
        expect(".o_we_url_link").toHaveText("Task name | Project name");
        expect(".o_we_description_link_preview").toHaveText("Test description");

        await click(".o_we_replace_title_btn");
        await animationFrame();

        expect(".o_we_replace_title_btn").toHaveCount(0);
        expect(cleanLinkArtifacts(el.textContent)).toBe("Task name | Project name");
    });
    test("test external link preview", async () => {
        onRpc("/html_editor/link_preview_external", () => {
            return {
                og_description:
                    "From ERP to CRM, eCommerce and CMS. Download Odoo or use it in the cloud. Grow Your Business.",
                og_image: "https://www.odoo.com/web/image/41207129-1abe7a15/homepage-seo.png",
                og_title: "Open Source ERP and CRM | Odoo",
                og_type: "website",
                og_site_name: "Odoo",
                source_url: "http://odoo.com/",
            };
        });
        const { editor } = await setupEditor(`<p>[]</p>`);
        await insertText(editor, "/link");
        await animationFrame();
        await click(".o-we-command-name:first");
        await contains(".o-we-linkpopover input.o_we_href_input_link").fill("http://odoo.com/");
        await animationFrame();
        expect(".o_we_replace_title_btn").toHaveCount(1);
        expect(".o_extra_info_card").toHaveCount(1);
        expect(".o_we_url_link").toHaveText("Open Source ERP and CRM | Odoo");
        expect(".o_we_description_link_preview").toHaveText(
            "From ERP to CRM, eCommerce and CMS. Download Odoo or use it in the cloud. Grow Your Business."
        );
    });
    test("test internal metadata cached correctly", async () => {
        onRpc("/html_editor/link_preview_internal", () => {
            expect.step("/html_editor/link_preview_internal");
            return {
                description: markup("<p>Test description</p>"),
                link_preview_name: "Task name | Project name",
            };
        });
        onRpc("/odoo/cachetest/8", () => new Response("", { status: 200 }));
        const { editor } = await setupEditor(`<p>abc[]</p>`);
        await insertText(editor, "/link");
        await animationFrame();
        await click(".o-we-command-name:first");
        await contains(".o-we-linkpopover input.o_we_href_input_link").fill(
            window.location.origin + "/odoo/cachetest/8"
        );
        await animationFrame();
        expect.verifySteps(["/html_editor/link_preview_internal"]);
        expect(".o_we_url_link").toHaveText("Task name | Project name");

        const pNode = queryOne("p");
        setSelection({
            anchorNode: pNode,
            anchorOffset: 1,
            focusNode: pNode,
            focusOffset: 1,
        });
        await waitForNone(".o-we-linkpopover", { timeout: 1500 });

        const linkNode = queryOne("a");
        setSelection({
            anchorNode: linkNode,
            anchorOffset: 1,
            focusNode: linkNode,
            focusOffset: 1,
        });
        await waitFor(".o-we-linkpopover");
        expect.verifySteps([]);
    });
    test("test external metadata cached correctly", async () => {
        onRpc("/html_editor/link_preview_external", () => {
            expect.step("/html_editor/link_preview_external");
            return {
                og_description:
                    "From ERP to CRM, eCommerce and CMS. Download Odoo or use it in the cloud. Grow Your Business.",
                og_image: "https://www.odoo.com/web/image/41207129-1abe7a15/homepage-seo.png",
                og_title: "Open Source ERP and CRM | Odoo",
                og_type: "website",
                og_site_name: "Odoo",
                source_url: "http://odoo.com/",
            };
        });
        const { editor } = await setupEditor(`<p>[]</p>`);
        await insertText(editor, "/link");
        await animationFrame();
        await click(".o-we-command-name:first");
        await contains(".o-we-linkpopover input.o_we_href_input_link").fill("http://odoo.com/");
        await animationFrame();
        expect.verifySteps(["/html_editor/link_preview_external"]);
        expect(".o_we_url_link").toHaveText("Open Source ERP and CRM | Odoo");

        const pNode = queryOne("p");
        setSelection({
            anchorNode: pNode,
            anchorOffset: 1,
            focusNode: pNode,
            focusOffset: 1,
        });
        await waitForNone(".o-we-linkpopover", { timeout: 1500 });

        const linkNode = queryOne("a");
        setSelection({
            anchorNode: linkNode,
            anchorOffset: 1,
            focusNode: linkNode,
            focusOffset: 1,
        });
        await waitFor(".o-we-linkpopover");
        expect.verifySteps([]);
    });
});

describe("link in templates", () => {
    test("Should not remove a link with t-attf-href", async () => {
        const { el } = await setupEditor('<p>test<a t-attf-href="/test/1">li[]nk</a></p>');

        await waitFor(".o-we-linkpopover");
        expect(".o-we-linkpopover").toHaveCount(1);
        const pNode = queryOne("p");
        setSelection({
            anchorNode: pNode,
            anchorOffset: 0,
            focusNode: pNode,
            focusOffset: 0,
        });
        await waitForNone(".o-we-linkpopover", { timeout: 1500 });
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>[]test<a t-attf-href="/test/1">link</a></p>'
        );
    });
    test("Should not remove a link with t-att-href", async () => {
        const { el } = await setupEditor('<p>test<a t-att-href="/test/1">li[]nk</a></p>');

        await waitFor(".o-we-linkpopover");
        expect(".o-we-linkpopover").toHaveCount(1);
        const pNode = queryOne("p");
        setSelection({
            anchorNode: pNode,
            anchorOffset: 0,
            focusNode: pNode,
            focusOffset: 0,
        });
        await waitForNone(".o-we-linkpopover", { timeout: 1500 });
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>[]test<a t-att-href="/test/1">link</a></p>'
        );
    });
});

describe("links with inline image", () => {
    test("can add link to inline image + text", async () => {
        const { el } = await setupEditor(`<p>ab[cd<img src="${base64Img}">ef]g</p>`);
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-link");
        await contains(".o-we-linkpopover input.o_we_href_input_link", { timeout: 1500 }).edit("#");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            `<p>ab<a href="#">cd<img src="${base64Img}">ef[]</a>g</p>`
        );
    });
    test("can undo add link to inline image + text", async () => {
        const { editor, el } = await setupEditor(`<p>ab[cd<img src="${base64Img}">ef]g</p>`);
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-link");
        await contains(".o-we-linkpopover input.o_we_href_input_link", { timeout: 1500 }).edit("#");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            `<p>ab<a href="#">cd<img src="${base64Img}">ef[]</a>g</p>`
        );
        undo(editor);
        await animationFrame();
        expect(cleanLinkArtifacts(getContent(el))).toBe(`<p>ab[cd<img src="${base64Img}">ef]g</p>`);
    });
    test("can remove link from an inline image", async () => {
        const { el } = await setupEditor(`<p>ab<a href="#">cd<img src="${base64Img}">ef</a>g</p>`);
        await click("img");
        await waitFor(".o-we-toolbar");
        expect("button[name='unlink']").toHaveCount(1);
        await click("button[name='unlink']");
        await animationFrame();
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            `<p>ab<a href="#">cd[</a><img src="${base64Img}"><a href="#">]ef</a>g</p>`
        );
        expect(".o-we-linkpopover").toHaveCount(0);
    });
    test("can remove link from a selection of an inline image + text", async () => {
        const { el } = await setupEditor(
            `<p>ab<a href="#">c[d<img src="${base64Img}">e]f</a>g</p>`
        );
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-unlink");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            `<p>ab<a href="#">c</a>[d<img src="${base64Img}">e]<a href="#">f</a>g</p>`
        );
    });
    test("can remove link from a selection (ltr) with multiple inline images", async () => {
        const { el } = await setupEditor(
            `<p>ab<a href="#">c[d<img src="${base64Img}">e<img src="${base64Img}">f]g</a>h</p>`
        );
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-unlink");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            `<p>ab<a href="#">c</a>[d<img src="${base64Img}">e<img src="${base64Img}">f]<a href="#">g</a>h</p>`
        );
    });
    test("can remove link from a selection (rtl) with multiple inline images", async () => {
        const { el } = await setupEditor(
            `<p>ab<a href="#">c]d<img src="${base64Img}">e<img src="${base64Img}">f[g</a>h</p>`
        );
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-unlink");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            `<p>ab<a href="#">c</a>]d<img src="${base64Img}">e<img src="${base64Img}">f[<a href="#">g</a>h</p>`
        );
    });
    test("can remove link from a selection (ltr) with multiple inline images acrossing different links", async () => {
        const { el } = await setupEditor(
            `<p>ab<a href="#">c[d<img src="${base64Img}">e</a>xx<a href="#">f<img src="${base64Img}">g]h</a>i</p>`
        );
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-unlink");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            `<p>ab<a href="#">c</a>[d<img src="${base64Img}">exxf<img src="${base64Img}">g]<a href="#">h</a>i</p>`
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
});

describe("readonly mode", () => {
    test("popover should not display edit buttons in readonly mode", async () => {
        await setupEditor('<p><a class="o_link_readonly" href="#">link[]</a></p>');
        await waitFor(".o-we-linkpopover");
        // Copy link button should be available
        expect(".o-we-linkpopover .o_we_copy_link").toHaveCount(1);
        // Edit and unlink buttons should not be available
        expect(".o-we-linkpopover .o_we_edit_link").toHaveCount(0);
        expect(".o-we-linkpopover .o_we_remove_link").toHaveCount(0);
    });
});

describe("upload file via link popover", () => {
    test("should display upload button when url input is empty", async () => {
        const { editor } = await setupEditor("<p>[]<br></p>");
        execCommand(editor, "toggleLinkTools");
        await waitFor(".o-we-linkpopover");
        // Upload button should be visible
        expect("button:contains('Upload File')").toHaveCount(1);
        await click(".o_we_href_input_link");
        await press("a");
        await animationFrame();
        // Upload button should NOT be visible
        expect("button:contains('Upload File')").toHaveCount(0);
        await press("Backspace");
        await animationFrame();
        // Upload button should be visible again
        expect("button:contains('Upload File')").toHaveCount(1);
    });
    const patchUpload = (editor) => {
        const mockedUploadPromise = new Promise((resolve) => {
            patchWithCleanup(editor.services.uploadLocalFiles, {
                async upload() {
                    resolve();
                    return [{ id: 1, name: "file.txt", public: true, checksum: "123" }];
                },
            });
        });
        return mockedUploadPromise;
    };
    test("can create a link to an uploaded file", async () => {
        const { editor, el } = await setupEditor("<p>[]<br></p>");
        const mockedUpload = patchUpload(editor);
        execCommand(editor, "toggleLinkTools");
        await waitFor(".o-we-linkpopover");
        await click("button:contains('Upload File')");
        await mockedUpload;
        await animationFrame();
        // URL input gets filled with the attachments's URL
        const expectedUrl = "/web/content/1?unique=123&download=true";
        expect(".o_we_href_input_link").toHaveValue(expectedUrl);
        // Label input gets filled with the file's name
        expect(".o_we_label_link").toHaveValue("file.txt");
        await click(".o_we_apply_link");
        await animationFrame();
        // Created link has the correct href and label
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            `<p><a href="${expectedUrl}">file.txt[]</a></p>`
        );
    });

    test("label input does not get filled on file upload if it is already filled", async () => {
        const { editor } = await setupEditor("<p>[]<br></p>");
        const mockedUpload = patchUpload(editor);
        execCommand(editor, "toggleLinkTools");
        await waitFor(".o-we-linkpopover");
        // Fill label input
        await contains(".o-we-linkpopover input.o_we_label_link").fill("label");
        // Upload a file
        await click("button:contains('Upload File')");
        await mockedUpload;
        await animationFrame();
        // Label remains unchanged
        expect(".o_we_label_link").toHaveValue("label");
    });

    test("popover in preview mode should display the file's mimetype as favicon", async () => {
        onRpc("/web/dataset/call_kw/ir.attachment/read", () => {
            return [{ name: "file.txt", mimetype: "text/plain" }];
        });
        await setupEditor(
            '<p><a href="/web/content/1?download=true&unique=123">file.txt[]</a></p>'
        );
        const favIcon = await waitFor(".o_we_preview_favicon span.o_image");
        expect(favIcon).toHaveAttribute("data-mimetype", "text/plain");
    });
});
