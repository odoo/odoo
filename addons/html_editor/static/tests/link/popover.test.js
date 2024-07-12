import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, tick } from "@odoo/hoot-mock";
import { setContent, getContent, setSelection } from "../_helpers/selection";
import { setupEditor } from "../_helpers/editor";
import { waitUntil, waitFor, click, queryOne, press, select } from "@odoo/hoot-dom";
import { browser } from "@web/core/browser/browser";
import { insertText, splitBlock, insertLineBreak } from "../_helpers/user_actions";
import { contains } from "@web/../tests/web_test_helpers";
import { cleanLinkArtifacts } from "../_helpers/format";

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
        await waitUntil(() => !document.querySelector(".o-we-linkpopover"));
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
});

describe("popover should switch UI depending on editing state", () => {
    test("after clicking on edit button, the popover should switch to editing mode", async () => {
        await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        click(".o_we_edit_link");
        await waitFor(".o_we_href_input_link");
        expect(".o_we_label_link").toHaveValue("link");
        expect(".o_we_href_input_link").toHaveValue("http://test.com/");
    });
    test("after clicking on apply button, the selection should be restored", async () => {
        const { el } = await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        click(".o_we_edit_link");
        await waitFor(".o_we_href_input_link");
        click(".o_we_href_input_link");
        click(".o_we_apply_link");
        await waitFor(".o_we_edit_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="http://test.com/">li[]nk</a></p>'
        );
    });
    test("after editing the URL and clicking on apply button, the selection should be restored", async () => {
        const { el } = await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        click(".o_we_edit_link");
        await waitFor(".o_we_href_input_link");
        // This changes the selection to outside the editor.
        click(".o_we_href_input_link");
        await tick();
        press("a");
        click(".o_we_apply_link");
        await waitFor(".o_we_edit_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="http://test.com/a">li[]nk</a></p>'
        );
    });
    test("after clicking on apply button, the popover should be with the non editing mode, e.g. with three buttons", async () => {
        await setupEditor("<p>this is a <a>li[]nk</a></p>");
        await waitFor(".o-we-linkpopover");
        click(".o_we_href_input_link");
        click(".o_we_apply_link");
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
        click(".o_we_remove_link");
        await waitUntil(() => !document.querySelector(".o-we-linkpopover"));
        expect(getContent(el)).toBe("<p>this is a li[]nk</p>");
    });
    test("after edit the label, the text of the link should be updated", async () => {
        const { el } = await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        click(".o_we_edit_link");

        await contains(".o-we-linkpopover input.o_we_label_link").fill("new");
        click(".o_we_apply_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="http://test.com/">linknew[]</a></p>'
        );
    });
    test("when the label is empty, it should be set as the URL", async () => {
        const { el } = await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        click(".o_we_edit_link");
        await waitFor(".o_we_apply_link");

        await contains(".o-we-linkpopover input.o_we_label_link").clear();
        click(".o_we_apply_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="http://test.com/">http://test.com/[]</a></p>'
        );
    });
    test("after clicking on copy button, the url should be copied to clipboard", async () => {
        await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        click(".o_we_copy_link");
        await waitFor(".o_notification_body");
        expect(".o_notification_body").toHaveCount(1);
        await animationFrame();
        expect(".o-we-linkpopover").toHaveCount(0);
        expect(browser.navigator.clipboard.readTextSync()).toBe("http://test.com/");
    });
    test("when edit a link's label and URL to '', the link should be removed", async () => {
        const { editor, el } = await setupEditor(
            '<p>this is a <a href="http://test.com/">li[]nk</a></p>'
        );
        await waitFor(".o-we-linkpopover");
        click(".o_we_edit_link");

        await contains(".o-we-linkpopover input.o_we_label_link").clear();
        await contains(".o-we-linkpopover input.o_we_href_input_link").clear();
        // ZWNBSPs make space at the end of the paragraph to be visible
        expect(getContent(el)).toBe("<p>this is a \ufeff[]\ufeff</p>");
        editor.dispatch("CLEAN", { root: el });
        expect(getContent(el)).toBe("<p>this is a&nbsp;[]</p>");
    });
});

describe("Incorrect URL should be corrected", () => {
    test("when edit a link's URL to 'test.com', the link's URL should be corrected", async () => {
        const { el } = await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        click(".o_we_edit_link");

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
    test("when a link's URL is an phonenumber, the link's URL should start with tel://:", async () => {
        const { el } = await setupEditor("<p>this is a <a>li[]nk</a></p>");

        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("+1234567890");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="tel://+1234567890">li[]nk</a></p>'
        );
    });
});

describe("Link creation", () => {
    describe("Creation by space", () => {
        test("typing valid URL + space should convert to link", async () => {
            const { editor, el } = await setupEditor("<p>[]</p>");
            insertText(editor, "http://google.co.in");
            insertText(editor, " ");
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                '<p><a href="http://google.co.in">http://google.co.in</a> []</p>'
            );
        });
        test("typing invalid URL + space should not convert to link", async () => {
            const { editor, el } = await setupEditor("<p>[]</p>");
            insertText(editor, "www.odoo");
            insertText(editor, " ");
            expect(cleanLinkArtifacts(getContent(el))).toBe("<p>www.odoo []</p>");
        });
    });
    describe("Creation by powerbox", () => {
        test("click on link command in powerbox should create a link element and open the linkpopover", async () => {
            const { editor, el } = await setupEditor("<p>ab[]</p>");
            insertText(editor, "/link");
            await animationFrame();
            expect(".active .o-we-command-name").toHaveText("Link");

            click(".o-we-command-name:first");
            expect(cleanLinkArtifacts(getContent(el))).toBe("<p>ab<a>[]</a></p>");
            await waitFor(".o-we-linkpopover");
            expect(".o-we-linkpopover").toHaveCount(1);
        });

        test("when create a new link by powerbox and not input anything, the link should be removed", async () => {
            const { editor, el } = await setupEditor("<p>ab[]</p>");
            insertText(editor, "/link");
            await animationFrame();
            click(".o-we-command-name:first");
            await waitFor(".o-we-linkpopover");
            expect(".o-we-linkpopover").toHaveCount(1);
            expect(cleanLinkArtifacts(getContent(el))).toBe("<p>ab<a>[]</a></p>");

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
            insertText(editor, "/link");
            await animationFrame();
            click(".o-we-command-name:first");

            await contains(".o-we-linkpopover input.o_we_href_input_link").fill("test.com");
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                '<p>ab<a href="http://test.com">test.com[]</a></p>'
            );
        });
        test("Should be able to insert link on empty p", async () => {
            const { editor, el } = await setupEditor("<p>[]</p>");
            insertText(editor, "/link");
            await animationFrame();
            click(".o-we-command-name:first");

            await contains(".o-we-linkpopover input.o_we_href_input_link").fill("#");
            expect(cleanLinkArtifacts(getContent(el))).toBe('<p><a href="#">#[]</a></p>');
        });
        test("should insert a link and preserve spacing", async () => {
            const { editor, el } = await setupEditor("<p>a []&nbsp;&nbsp;b</p>");
            insertText(editor, "/link");
            await animationFrame();
            click(".o-we-command-name:first");
            await contains(".o-we-linkpopover input.o_we_label_link").fill("link");
            await contains(".o-we-linkpopover input.o_we_href_input_link").fill("#");
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                '<p>a <a href="#">link[]</a>&nbsp;&nbsp;b</p>'
            );
        });
        test("should insert a link then create a new <p>", async () => {
            const { editor, el } = await setupEditor("<p>ab[]</p>");
            insertText(editor, "/link");
            await animationFrame();
            click(".o-we-command-name:first");
            await contains(".o-we-linkpopover input.o_we_label_link").fill("link");
            await contains(".o-we-linkpopover input.o_we_href_input_link").fill("#");
            // press("Enter");
            splitBlock(editor);
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                '<p>ab<a href="#">link</a></p><p placeholder="Type "/" for commands" class="o-we-hint">[]<br></p>'
            );
        });
        test("should insert a link then create a new <p>, and another character", async () => {
            const { editor, el } = await setupEditor("<p>a[]b</p>");
            insertText(editor, "/link");
            await animationFrame();
            click(".o-we-command-name:first");
            await contains(".o-we-linkpopover input.o_we_label_link").fill("link");
            await contains(".o-we-linkpopover input.o_we_href_input_link").fill("#");
            // press("Enter");
            splitBlock(editor);
            insertText(editor, "D");
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                '<p>a<a href="#">link</a></p><p>D[]b</p>'
            );
        });
        test("should insert a link then insert a <br>", async () => {
            const { editor, el } = await setupEditor("<p>a[]b</p>");
            insertText(editor, "/link");
            await animationFrame();
            click(".o-we-command-name:first");
            await contains(".o-we-linkpopover input.o_we_label_link").fill("link");
            await contains(".o-we-linkpopover input.o_we_href_input_link").fill("#");
            // press("Enter");
            insertLineBreak(editor);
            expect(cleanLinkArtifacts(getContent(el))).toBe('<p>a<a href="#">link</a><br>[]b</p>');
        });
        test("should insert a link then insert a <br> and another character", async () => {
            const { editor, el } = await setupEditor("<p>a[]b</p>");
            insertText(editor, "/link");
            await animationFrame();
            click(".o-we-command-name:first");
            await contains(".o-we-linkpopover input.o_we_label_link").fill("link");
            await contains(".o-we-linkpopover input.o_we_href_input_link").fill("#");
            // press("Enter");
            insertLineBreak(editor);
            insertText(editor, "D");
            expect(cleanLinkArtifacts(getContent(el))).toBe('<p>a<a href="#">link</a><br>D[]b</p>');
        });
    });
    describe("Creation by toolbar", () => {
        test("should convert all selected text to link", async () => {
            const { el } = await setupEditor("<p>[Hello]</p>");
            await waitFor(".o-we-toolbar");
            click(".o-we-toolbar .fa-link");
            await contains(".o-we-linkpopover input.o_we_href_input_link").edit("#");
            expect(cleanLinkArtifacts(getContent(el))).toBe('<p><a href="#">Hello[]</a></p>');
        });
        test("should set the link on two existing characters", async () => {
            const { el } = await setupEditor("<p>H[el]lo</p>");
            await waitFor(".o-we-toolbar");
            click(".o-we-toolbar .fa-link");
            await contains(".o-we-linkpopover input.o_we_href_input_link").edit("#");
            expect(cleanLinkArtifacts(getContent(el))).toBe('<p>H<a href="#">el[]</a>lo</p>');
        });
        test("should be correctly unlink/link", async () => {
            const { el } = await setupEditor('<p>aaaa[b<a href="http://test.com/">cd</a>e]f</p>');
            await waitFor(".o-we-toolbar");

            click(".o-we-toolbar .fa-unlink");
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
            click(".o-we-toolbar .fa-link");
            await contains(".o-we-linkpopover input.o_we_href_input_link").edit("#");
            expect(cleanLinkArtifacts(getContent(el))).toBe('<p>aaa<a href="#">ab[]</a>cdef</p>');
        });
        test("should remove link when click away without inputting url", async () => {
            const { el } = await setupEditor("<p>H[el]lo</p>");
            await waitFor(".o-we-toolbar");
            click(".o-we-toolbar .fa-link");
            await waitFor(".o-we-linkpopover");
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

            click(".o-we-toolbar .fa-link");
            await waitFor(".o-we-linkpopover");
            expect(".o-we-linkpopover").toHaveCount(1);
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                '<p>a<a href="http://test.com/">bcd[]</a>ef</p>'
            );
        });
        test("when selection includes a link and click the link icon in toolbar, the link should be extended", async () => {
            const { el } = await setupEditor('<p>a[b<a href="http://test.com/">cd</a>e]f</p>');
            await waitFor(".o-we-toolbar");

            click(".o-we-toolbar .fa-link");
            await waitFor(".o-we-linkpopover");
            expect(".o-we-linkpopover").toHaveCount(1);
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                '<p>a<a href="http://test.com/">bcde[]</a>f</p>'
            );
        });
        test("when selection includes another block and the link extending stays inside of the block", async () => {
            const { el } = await setupEditor(
                '<p>a[b<a href="http://test.com/">cd</a>ef</p><p>gh]</p>'
            );
            await waitFor(".o-we-toolbar");

            click(".o-we-toolbar .fa-link");
            await waitFor(".o-we-linkpopover");
            expect(".o-we-linkpopover").toHaveCount(1);
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                '<p>a<a href="http://test.com/">bcdef[]</a></p><p>gh</p>'
            );
        });
    });
});

describe("Link formatting in the popover", () => {
    test("click on link, the link popover should load the current format correctly", async () => {
        await setupEditor(
            '<p><a href="http://test.com/" class="btn btn-outline-primary rounded-circle btn-lg">link2[]</a></p>'
        );
        await waitFor(".o-we-linkpopover");
        click(".o_we_edit_link");
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
        click(".o_we_edit_link");

        const linkPreviewEl = await waitFor("#link-preview");
        expect(linkPreviewEl).toHaveClass([
            "btn",
            "rounded-circle",
            "btn-fill-secondary",
            "btn-sm",
        ]);
        expect(queryOne('select[name="link_type"]').selectedIndex).toBe(2);
        expect(queryOne('select[name="link_style_size"]').selectedIndex).toBe(0);
        expect(queryOne('select[name="link_style_shape"]').selectedIndex).toBe(5);

        click('select[name="link_type"');
        select("primary");
        click('select[name="link_style_size"');
        select("lg");
        click('select[name="link_style_shape"');
        select("rounded-circle");
        await animationFrame();
        expect(linkPreviewEl).toHaveClass(["btn", "btn-primary", "rounded-circle", "btn-lg"]);
    });
    test("after applying the link format, the link's format should be updated", async () => {
        const { el } = await setupEditor('<p><a href="http://test.com/">link2[]</a></p>');
        await waitFor(".o-we-linkpopover");
        click(".o_we_edit_link");
        await waitFor("#link-preview");
        expect(queryOne('select[name="link_type"]').selectedIndex).toBe(0);

        click('select[name="link_type"');
        select("secondary");
        await animationFrame();
        click('select[name="link_style_shape"');
        select("flat");
        await animationFrame();

        const linkPreviewEl = queryOne("#link-preview");
        expect(linkPreviewEl).toHaveClass(["btn", "btn-secondary", "flat"]);

        click(".o_we_apply_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.com/" class="btn btn-secondary flat">link2[]</a></p>'
        );
    });
    test("no preview of the link when the url is empty", async () => {
        await setupEditor("<p><a>link2[]</a></p>");
        await waitFor(".o-we-linkpopover");
        expect("#link-preview").toHaveCount(0);
    });
    test("when no label input, the link preview should have the content of the url", async () => {
        const { editor } = await setupEditor("<p>ab[]</p>");
        insertText(editor, "/link");
        await animationFrame();
        click(".o-we-command-name:first");
        await waitFor(".o-we-linkpopover");

        queryOne(".o_we_href_input_link").focus();
        for (const char of "newtest.com") {
            press(char);
        }
        await animationFrame();
        const linkPreviewEl = queryOne("#link-preview");
        expect(linkPreviewEl).toHaveText("newtest.com");
    });
});

describe("shortcut", () => {
    test("create a link with shortcut", async () => {
        const { el } = await setupEditor(`<p>[]</p>`);

        press(["ctrl", "k"]);
        await animationFrame();
        click(".o_command_name:first");
        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("test.com");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.com">test.com[]</a></p>'
        );
    });
    test("should be able to create link with ctrl+k and ctrl+k", async () => {
        const { el } = await setupEditor(`<p>[]</p>`);

        press(["ctrl", "k"]);
        await animationFrame();
        press(["ctrl", "k"]);
        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("test.com");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.com">test.com[]</a></p>'
        );
    });
    test("should be able to create link with ctrl+k , and should make link on two existing characters", async () => {
        const { el } = await setupEditor(`<p>H[el]lo</p>`);

        press(["ctrl", "k"]);
        await animationFrame();
        press(["ctrl", "k"]);
        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("test.com");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>H<a href="http://test.com">el[]</a>lo</p>'
        );
    });
    test("Press enter to apply when create a link", async () => {
        const { el } = await setupEditor(`<p><a>li[]nk</a></p>`);

        await contains(".o-we-linkpopover input.o_we_href_input_link").fill("test.com");
        press("Enter");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.com">li[]nk</a></p>'
        );
    });
});
