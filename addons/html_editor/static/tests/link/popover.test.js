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
import { expectElementCount } from "../_helpers/ui_expectations";
import { insertLineBreak, insertText, splitBlock, undo } from "../_helpers/user_actions";
import { execCommand } from "../_helpers/userCommands";
import { MAIN_PLUGINS, NO_EMBEDDED_COMPONENTS_FALLBACK_PLUGINS } from "@html_editor/plugin_sets";

const base64Img =
    "data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAAUA\n        AAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO\n            9TXL0Y4OHwAAAABJRU5ErkJggg==";

describe("should open a popover", () => {
    test("should open a popover when the selection is inside a link and close outside of a link", async () => {
        const { el } = await setupEditor("<p>this is a <a>link</a></p>");
        await expectElementCount(".o-we-linkpopover", 0);
        // selection inside a link
        setContent(el, "<p>this is a <a>li[]nk</a></p>");
        await expectElementCount(".o-we-linkpopover", 1);
        // selection outside a link
        setContent(el, "<p>this []is a <a>link</a></p>");
        await expectElementCount(".o-we-linkpopover", 0);
    });
    test("should open a popover when the selection is inside a link and stay open if selection move in the same link", async () => {
        const { el } = await setupEditor(
            '<p>this []is a <a href="http://test.test/">l<b>in</b>k</a></p>'
        );
        await expectElementCount(".o-we-linkpopover", 0);
        // selection inside a link
        const aNode = queryOne("a");
        setSelection({
            anchorNode: aNode,
            anchorOffset: 3,
            focusNode: aNode,
            focusOffset: 3,
        });
        await expectElementCount(".o-we-linkpopover", 1);
        // FEFF is taken into account in the index
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="http://test.test/">l<b>in</b>[]k</a></p>'
        );
        // Another selection in the same link
        setSelection({
            anchorNode: aNode,
            anchorOffset: 0,
            focusNode: aNode,
            focusOffset: 0,
        });
        await animationFrame();
        await expectElementCount(".o-we-linkpopover", 1);
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="http://test.test/">[]l<b>in</b>k</a></p>'
        );
    });
    test("link popover should have input field for href when the link doesn't have href", async () => {
        await setupEditor("<p>this is a <a>li[]nk</a></p>");
        await expectElementCount(".o-we-linkpopover", 1);
        expect(".o_we_label_link").toHaveValue("link");
        expect(".o_we_href_input_link").toHaveValue("");
    });
    test("link popover should have buttons for link operation when the link has href", async () => {
        await setupEditor('<p>this is a <a href="http://test.test/">li[]nk</a></p>');
        await expectElementCount(".o-we-linkpopover", 1);
        expect(".o_we_copy_link").toHaveCount(1);
        expect(".o_we_edit_link").toHaveCount(1);
        expect(".o_we_remove_link").toHaveCount(1);
    });
    test("link popover should not have the remove button when link is unremovable", async () => {
        await setupEditor('<p>a<a class="oe_unremovable" href="http://test.test/">bcd[]</a>e</p>');
        await expectElementCount(".o-we-linkpopover", 1);
        expect(".o_we_copy_link").toHaveCount(1);
        expect(".o_we_edit_link").toHaveCount(1);
        expect(".o_we_remove_link").toHaveCount(0);
    });
    test("link popover should not repositioned when clicking in the input field", async () => {
        await setupEditor("<p>this is a <a>li[]nk</a></p>");
        await waitFor(".o_we_href_input_link");
        const style = queryOne(".o-we-linkpopover").parentElement.style.cssText;
        queryOne(".o_we_href_input_link").focus();
        await animationFrame();
        expect(queryOne(".o-we-linkpopover").parentElement).toHaveAttribute("style", style);
    });
    test("link popover should close when clicking on a contenteditable false element", async () => {
        await setupEditor(
            '<p><a href="http://test.test/">li[]nk</a> <a contenteditable="false">uneditable link</a></p>'
        );
        await waitFor(".o-we-linkpopover");
        expect(".o-we-linkpopover").toHaveCount(1);
        // click on an uneditable element
        const nodeEl = queryOne("a[contenteditable='false']");
        setSelection({ anchorNode: nodeEl, anchorOffset: 0 });
        await waitForNone(".o-we-linkpopover", { timeout: 1500 });
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
        // This changes the selection to outside the editor.
        await click(".o_we_href_input_link");
        await tick();
        await fill("test-href.com");
        await waitFor(".o_we_apply_link:not([disabled])");
        await click(".o_we_apply_link");
        await waitFor(".o_we_edit_link");
        await expectElementCount(".o-we-linkpopover", 1);
        expect(".o_we_copy_link").toHaveCount(1);
        expect(".o_we_edit_link").toHaveCount(1);
        expect(".o_we_remove_link").toHaveCount(1);
    });
    test("changes to link text done before clicking on edit button should be kept if discard button is pressed", async () => {
        const { editor, el } = await setupEditor(
            '<p>this is a <a href="http://test.com/">link[]</a></p>'
        );
        await waitFor(".o-we-linkpopover", { timeout: 1500 });
        await insertText(editor, "ABCD");
        // Discard should not remove changes done directly to the link text
        await click(".o_we_edit_link");
        await waitFor(".o_we_href_input_link");
        await click(".o_we_discard_link");
        await waitFor(".o_we_edit_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="http://test.com/">linkABCD[]</a></p>'
        );
    });
    test("should open seo advanced popup when gear icon is clicked", async () => {
        await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await waitFor(".o_we_href_input_link");
        await click(".o_we_href_input_link");
        await click(".o-we-linkpopover .fa-gear");
        await expectElementCount(".o_advance_option_panel", 1);
        expect(".o_advance_option_panel .o_seo_option_row").toHaveCount(4);
    });
    test("should add rel='nofollow' when checkbox is selected and applied", async () => {
        const { el } = await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await waitFor(".o_we_href_input_link");
        await click(".o_we_href_input_link");
        await click(".o-we-linkpopover .fa-gear");
        await expectElementCount(".o_advance_option_panel", 1);
        await contains(".o_seo_option_row:nth-of-type(1) input[type='checkbox']").click();
        await click(".o_advance_option_panel .fa-angle-left");
        await waitFor(".o-we-linkpopover");
        await contains(".o_we_apply_link").click();
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="http://test.com/" rel="nofollow">li[]nk</a></p>'
        );
    });
    test("should add and remove relAttribute in anchor tag when checkbox is selected and applied", async () => {
        const { el } = await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await waitFor(".o_we_href_input_link");
        await click(".o_we_href_input_link");
        await click(".o-we-linkpopover .fa-gear");
        await expectElementCount(".o_advance_option_panel", 1);
        await contains(".o_seo_option_row:nth-of-type(1) input[type='checkbox']").click();
        await contains(".o_seo_option_row:nth-of-type(2) input[type='checkbox']").click();
        await contains(".o_seo_option_row:nth-of-type(3) input[type='checkbox']").click();
        await click(".o_advance_option_panel .fa-angle-left");
        await waitFor(".o-we-linkpopover");
        await contains(".o_we_apply_link").click();
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="http://test.com/" rel="nofollow noreferrer sponsored">li[]nk</a></p>'
        );
        await click(".o_we_edit_link");
        await waitFor(".o_we_href_input_link");
        await click(".o_we_href_input_link");
        await click(".o-we-linkpopover .fa-gear");
        await contains(".o_seo_option_row:nth-of-type(1) input[type='checkbox']").click();
        await click(".o_advance_option_panel .fa-angle-left");
        await waitFor(".o-we-linkpopover");
        await contains(".o_we_apply_link").click();
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="http://test.com/" rel="noreferrer sponsored">li[]nk</a></p>'
        );
    });
    test("should add _blank attribute on open in a new window is checked", async () => {
        const { el } = await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await waitFor(".o_we_href_input_link");
        await click(".o_we_href_input_link");
        await click(".o-we-linkpopover .fa-gear");
        await expectElementCount(".o_advance_option_panel", 1);
        await contains(".o_advance_option_panel .target-blank-option").click();
        await contains(".o_seo_option_row:nth-of-type(5) input[type='checkbox']").click();
        await click(".o_advance_option_panel .fa-angle-left");
        await waitFor(".o-we-linkpopover");
        await contains(".o_we_apply_link").click();
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="http://test.com/" rel="noopener" target="_blank">li[]nk</a></p>'
        );
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
    test("after edit the label, the text of the link should be updated (2)", async () => {
        const { el } = await setupEditor(
            '<p>this is a <a class="text-wrap" href="http://test.com/">li[]nk</a></p>'
        );
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");

        await contains(".o-we-linkpopover input.o_we_label_link").fill("new");
        await click(".o_we_apply_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a class="text-wrap o_link_in_selection" href="http://test.com/">linknew[]</a></p>'
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
    test("link popover should autoconvert an absolute URL if it's in the domain", async () => {
        onRpc("/html_editor/link_preview_internal", () => ({}));
        onRpc("/contactus", () => ({}));
        const absoluteUrlIndomain = `${window.origin}/contactus`;
        const { el } = await setupEditor(
            `<p>this is an absolute href targeting the domain <a href="${absoluteUrlIndomain}">absolute li[]nk</a></p>`,
            {
                config: {
                    allowStripDomain: true,
                },
            }
        );
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await waitFor(".o_we_apply_link");
        expect(".strip-domain-option input").toHaveCount(1);
        await click(".o_we_apply_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is an absolute href targeting the domain <a href="/contactus">absolute li[]nk</a></p>'
        );
    });
    test("relative URLs should be kept relative URLs", async () => {
        onRpc("/html_editor/link_preview_internal", () => ({}));
        onRpc("/contactus", () => ({}));
        const { el } = await setupEditor('<p>this is a <a href="/contactus">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await waitFor(".o_we_apply_link");
        await click(".o_we_apply_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="/contactus">li[]nk</a></p>'
        );
    });
    test("Should properly show the preview if fetching metadata fails", async () => {
        const id = Math.random().toString();
        onRpc("/html_editor/link_preview_internal", () =>
            Promise.reject(new Error(`No data ${id}`))
        );
        onRpc("/contactus", () => ({}));
        const originalConsoleWarn = console.warn.bind(console);
        patchWithCleanup(console, {
            warn: (msg, error, ...args) => {
                if (!error?.message?.includes?.(id)) {
                    originalConsoleWarn(msg, error, ...args);
                }
            },
        });
        const { el } = await setupEditor('<p><a href="/contactus">a[]b</a></p>');
        await waitFor(".o-we-linkpopover");
        expect(cleanLinkArtifacts(getContent(el))).toBe('<p><a href="/contactus">a[]b</a></p>');
    });
    test("after clicking on copy button, the url should be copied to clipboard", async () => {
        await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_copy_link");
        await waitFor(".o_notification_bar.bg-success");
        const notifications = queryAllTexts(".o_notification_body");
        expect(notifications).toInclude("Link copied to clipboard.");
        await animationFrame();
        await expectElementCount(".o-we-linkpopover", 0);
        await expect(navigator.clipboard.readText()).resolves.toBe("http://test.com/");
    });
});

describe("Incorrect URL should be corrected", () => {
    test("when edit a link's URL to 'test.com', the link's URL should be corrected", async () => {
        const { el } = await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");

        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("newtest.com");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>this is a <a href="https://newtest.com">li[]nk</a></p>'
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
        test("typing valid URL without protocol + space should convert to https link", async () => {
            const { editor, el } = await setupEditor("<p>[]</p>");
            await insertText(editor, "google.com");
            await insertText(editor, " ");
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                '<p><a href="https://google.com">google.com</a>&nbsp;[]</p>'
            );
        });
        test("typing valid http URL + space should convert to http link", async () => {
            const { editor, el } = await setupEditor("<p>[]</p>");
            await insertText(editor, "http://google.com");
            await insertText(editor, " ");
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                '<p><a href="http://google.com">http://google.com</a>&nbsp;[]</p>'
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

            await contains(".o-we-linkpopover input.o_we_href_input_link").fill(
                "http://test.test/"
            );
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                '<p><a href="http://test.test/">http://test.test/[]</a></p>'
            );
        });
        test("Should be able to insert button on empty p", async () => {
            const { editor, el } = await setupEditor("<p>[]<br></p>");
            await insertText(editor, "/button");
            await animationFrame();
            await click(".o-we-command-name:first");

            await contains(".o-we-linkpopover input.o_we_href_input_link").fill(
                "http://test.test/"
            );
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                '<p><a href="http://test.test/" class="btn btn-primary">http://test.test/[]</a></p>'
            );
        });
        test("Should keep http protocol on valid http url", async () => {
            const { editor, el } = await setupEditor("<p>[]<br></p>");
            await insertText(editor, "/link");
            await animationFrame();
            await click(".o-we-command-name:first");

            await contains(".o-we-linkpopover input.o_we_href_input_link").fill(
                "http://google.com"
            );
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
            await contains(".o-we-linkpopover input.o_we_href_input_link").fill(
                "http://test.test/"
            );
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
            await contains(".o-we-linkpopover input.o_we_href_input_link").fill(
                "http://test.test/"
            );
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
            await contains(".o-we-linkpopover input.o_we_href_input_link").fill(
                "http://test.test/"
            );
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
            await contains(".o-we-linkpopover input.o_we_href_input_link").fill(
                "http://test.test/"
            );
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
            await contains(".o-we-linkpopover input.o_we_href_input_link").fill(
                "http://test.test/"
            );
            // press("Enter");
            insertLineBreak(editor);
            await insertText(editor, "D");
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                '<p>a<a href="http://test.test/">link</a><br>D[]b</p>'
            );
        });
    });
    describe("Creation by toolbar", () => {
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
            await contains(".o-we-linkpopover input.o_we_href_input_link").edit(
                "http://test.test/"
            );
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
            await contains(".o-we-linkpopover input.o_we_href_input_link").edit(
                "http://test.test/"
            );
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
            await contains(".o-we-linkpopover input.o_we_href_input_link").edit(
                "http://test.test/"
            );
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
        test("when you open link popover, url label should be focus by default", async () => {
            const { el } = await setupEditor("<p>[Hello]</p>");
            await waitFor(".o-we-toolbar");
            await click(".o-we-toolbar .fa-link");
            await waitFor(".o-we-linkpopover", { timeout: 1500 });
            expect(".o-we-linkpopover input.o_we_label_link").toBeFocused();

            queryOne(".o-we-linkpopover input.o_we_href_input_link").focus();
            await fill("test.com");
            await waitFor(".o_we_apply_link:not([disabled])");
            await click(".o_we_apply_link");
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                '<p><a href="https://test.com">Hello[]</a></p>'
            );
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
            await setupEditor(
                '<p><strong>abc<a href="http://test.com/">de</a>te[st</strong> m]e</p>'
            );
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
            await contains(".o-we-linkpopover input.o_we_href_input_link").edit(
                "http://test.test/"
            );
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
});

describe.tags("desktop");
describe("Link formatting in the popover", () => {
    test("click on link, the link popover should load the current format correctly", async () => {
        await setupEditor(
            '<p><a href="http://test.com/" class="btn btn-fill-primary">link2[]</a></p>'
        );
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await animationFrame();
        expect(".o_we_label_link").toHaveValue("link2");
        expect(".o_we_href_input_link").toHaveValue("http://test.com/");
        expect(queryOne('select[name="link_type"]').selectedIndex).toBe(1);
    });
    test("after changing the link format, the link should be updated", async () => {
        const { el } = await setupEditor(
            '<p><a href="http://test.com/" class="btn btn-fill-secondary">link2[]</a></p>'
        );
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await animationFrame();

        expect(queryOne('select[name="link_type"]').selectedIndex).toBe(2);

        await click('select[name="link_type"');
        await select("primary");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.com/" class="btn btn-primary">link2</a></p>'
        );
    });
    test("after changing the link format, the link should be updated (2)", async () => {
        const { el } = await setupEditor(
            '<p><a href="http://test.com/" class="btn btn-secondary">link2[]</a></p>'
        );
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await animationFrame();

        expect(queryOne('select[name="link_type"]').selectedIndex).toBe(2);

        await click('select[name="link_type"');
        await select("primary");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.com/" class="btn btn-primary">link2</a></p>'
        );
    });
    test("after changing the link format, the link should be updated (3)", async () => {
        const { el } = await setupEditor(
            '<p><a href="http://test.com/" class="random-css-class btn btn-outline-secondary text-muted">link2[]</a></p>'
        );
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await animationFrame();

        expect(queryOne('select[name="link_type"]').selectedIndex).toBe(2);

        await click('select[name="link_type"');
        await select("primary");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.com/" class="random-css-class text-muted btn btn-primary">link2</a></p>'
        );
    });
    test("after applying the link format, the link's format should be updated", async () => {
        const { el } = await setupEditor('<p><a href="http://test.com/">link2[]</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await animationFrame();
        expect(queryOne('select[name="link_type"]').selectedIndex).toBe(0);

        await click('select[name="link_type"');
        await select("secondary");

        await click(".o_we_apply_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.com/" class="btn btn-secondary">link2[]</a></p>'
        );
    });
    const styleForceColor = `p > a.btn { color: black !important; border-color: gray !important }`;
    test("custom link format fill with solid color should be stored as background-color", async () => {
        const { el } = await setupEditor(
            '<p><a href="http://test.com/" class="btn btn-secondary">link2[]</a></p>',
            {
                config: {
                    allowCustomStyle: true,
                },
                styleContent: styleForceColor,
            }
        );
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await animationFrame();

        expect(queryOne('select[name="link_type"]').selectedIndex).toBe(2);

        await click('select[name="link_type"');
        await select("custom");
        await animationFrame();
        await click(".o_we_color_preview.custom-fill-picker");
        await animationFrame();
        await click('[data-color="#FF9C00"]');
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.com/" class="btn btn-custom" style="color: rgb(0, 0, 0); background-color: #FF9C00; border-width: 1px; border-color: rgb(128, 128, 128); border-style: solid; ">link2</a></p>'
        );
    });
    test("custom link format fill with gradient should be stored as background-image", async () => {
        const { el } = await setupEditor(
            '<p><a href="http://test.com/" class="btn btn-secondary">link2[]</a></p>',
            {
                config: {
                    allowCustomStyle: true,
                },
                styleContent: styleForceColor,
            }
        );
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await animationFrame();

        expect(queryOne('select[name="link_type"]').selectedIndex).toBe(2);

        await click('select[name="link_type"');
        await select("custom");
        await animationFrame();
        await click(".o_we_color_preview.custom-fill-picker");
        await animationFrame();
        await click(".gradient-tab");
        await animationFrame();
        await click(".o_gradient_color_button");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.com/" class="btn btn-custom" style="color: rgb(0, 0, 0); background-image: linear-gradient(135deg, rgb(255, 204, 51) 0%, rgb(226, 51, 255) 100%); border-width: 1px; border-color: rgb(128, 128, 128); border-style: solid; ">link2</a></p>'
        );
    });
    test("clicking the discard button should revert the link format", async () => {
        const { el } = await setupEditor('<p><a href="http://test.com/">link1[]</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await contains(".o-we-linkpopover input.o_we_label_link").edit("link2");
        await click('select[name="link_type"]');
        await select("secondary");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.com/" class="btn btn-secondary">link2</a></p>'
        );
        await click(".o_we_discard_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.com/">link1[]</a></p>'
        );
    });
    test("should close link popover on discard without input", async () => {
        const { el, editor } = await setupEditor("<p>[]<br></p>");
        await insertText(editor, "/link");
        await animationFrame();
        await click(".o-we-command-name:first");
        await animationFrame();
        await waitFor(".o-we-linkpopover");

        await contains(".o_we_discard_link").click();
        await expectElementCount(".o-we-linkpopover", 0);
        expect(getContent(el)).toBe(
            `<p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`
        );
    });
    test("clicking the discard button should revert the link creation", async () => {
        const { el } = await setupEditor("<p>[link1]</p>");
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-link");

        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("#", {
            confirm: false,
        });

        await click('select[name="link_type"]');
        await select("secondary");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="#" class="btn btn-secondary">link1</a></p>'
        );
        await click(".o_we_discard_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe("<p>[link1]</p>");
        await animationFrame();
        await waitForNone(".o-we-linkpopover"); // Popover should be closed.
        await animationFrame();
        await waitFor(".o-we-toolbar"); // Toolbar should re open.
    });
    test("when no label input, the link should have the content of the url", async () => {
        const { el, editor } = await setupEditor("<p>ab[]</p>");
        await insertText(editor, "/link");
        await animationFrame();
        await click(".o-we-command-name:first");
        await waitFor(".o-we-linkpopover");

        queryOne(".o_we_href_input_link").focus();
        for (const char of "newtest.com") {
            await press(char);
        }
        await animationFrame();
        await click(".o_we_apply_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>ab<a href="https://newtest.com">newtest.com[]</a></p>'
        );
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
    test("should trap focus within link popover when using Tab and Shift+Tab", async () => {
        await setupEditor(`<p><a>li[]nk</a></p>`);
        await expectElementCount(".o-we-linkpopover", 1);

        // Tab through all focusable elements
        await press("Tab");
        await animationFrame();
        expect(".o_we_href_input_link").toBeFocused();
        await press("Tab");
        await animationFrame();
        expect("select[name='link_type']").toBeFocused();
        await press("Tab");
        await animationFrame();
        expect(".form-check-input").toBeFocused();
        await press("Tab");
        await animationFrame();
        expect(".o_we_discard_link").toBeFocused();

        // One more Tab should wrap to first element
        await press("Tab");
        await animationFrame();
        expect(".o_we_label_link").toBeFocused();

        // Shift+Tab should wrap to Last element
        await press(["Shift", "Tab"]);
        await animationFrame();
        expect(".o_we_discard_link").toBeFocused();
    });
});

describe("link preview", () => {
    test("test internal link preview", async () => {
        onRpc("/html_editor/link_preview_internal", () => ({
            description: markup("Test description"),
            link_preview_name: "Task name | Project name",
        }));
        onRpc("/odoo/project/1/tasks/8", () => "");
        const { editor, el } = await setupEditor(`<p>[]<br></p>`, {
            config: {
                allowStripDomain: false,
            },
        });
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
        onRpc("/html_editor/link_preview_external", () => ({
            og_description:
                "From ERP to CRM, eCommerce and CMS. Download Odoo or use it in the cloud. Grow Your Business.",
            og_image: "https://www.odoo.com/web/image/41207129-1abe7a15/homepage-seo.png",
            og_title: "Open Source ERP and CRM | Odoo",
            og_type: "website",
            og_site_name: "Odoo",
            source_url: "http://odoo.com/",
        }));
        const { editor } = await setupEditor(`<p>[]<br></p>`);
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
        onRpc("/odoo/cachetest/8", () => "");
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
    test("should use cached metadata even if protocol changes", async () => {
        onRpc("/html_editor/link_preview_internal", () => {
            expect.step("/html_editor/link_preview_internal");
            return {
                description: markup("<p>Protocol Testing</p>"),
                link_preview_name: "Internal Page | Test",
            };
        });

        const currentProtocol = window.location.protocol;
        onRpc("/odoo/cachetest/8", (request) => {
            const urlProtocol = new URL(request.url).protocol;
            expect(urlProtocol).toBe(currentProtocol);
            return "";
        });

        const { editor } = await setupEditor(`<p>abc[]</p>`, {
            config: {
                allowStripDomain: false,
            },
        });
        await insertText(editor, "/link");
        await animationFrame();
        await click(".o-we-command-name:first");

        const wrongProtocol = currentProtocol === "https:" ? "http:" : "https:";
        const testUrl = `${wrongProtocol}//${window.location.host}/odoo/cachetest/8`;

        await contains(".o-we-linkpopover input.o_we_href_input_link").fill(testUrl);
        await animationFrame();
        expect.verifySteps(["/html_editor/link_preview_internal"]);
        expect(".o_we_url_link").toHaveText("Internal Page | Test");

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
        const title = "Open Source ERP and CRM | Odoo";
        const description =
            "From ERP to CRM, eCommerce and CMS. Download Odoo or use it in the cloud. Grow Your Business.";
        onRpc("/html_editor/link_preview_external", () => {
            expect.step("/html_editor/link_preview_external");
            return {
                og_description: description,
                og_image: "https://www.odoo.com/web/image/41207129-1abe7a15/homepage-seo.png",
                og_title: title,
                og_type: "website",
                og_site_name: "Odoo",
                source_url: "http://odoo.com/",
            };
        });
        const { editor } = await setupEditor(`<p>[]<br></p>`);
        await insertText(editor, "/link");
        await animationFrame();
        await click(".o-we-command-name:first");
        await contains(".o-we-linkpopover input.o_we_href_input_link").fill("http://odoo.com/");
        await animationFrame();
        expect.verifySteps(["/html_editor/link_preview_external"]);
        await waitFor(".o_we_description_link_preview");
        expect(".o_we_description_link_preview").toHaveText(description);
        expect(".o_we_url_link").toHaveText(title);

        const pNode = queryOne("p");
        setSelection({
            anchorNode: pNode,
            anchorOffset: 1,
        });
        await waitForNone(".o-we-linkpopover", { timeout: 1500 });

        const linkNode = queryOne("a");
        setSelection({
            anchorNode: linkNode,
            anchorOffset: 1,
        });
        await waitFor(".o-we-linkpopover");
        expect.verifySteps([]);
    });
    test("should change replace URL button to magic wand icon after selection change", async () => {
        onRpc("/html_editor/link_preview_external", () => ({
            og_description:
                "From ERP to CRM, eCommerce and CMS. Download Odoo or use it in the cloud. Grow Your Business.",
            og_image: "https://www.odoo.com/web/image/41207129-1abe7a15/homepage-seo.png",
            og_title: "Open Source ERP and CRM | Odoo",
            og_type: "website",
            og_site_name: "Odoo",
            source_url: "http://odoo.com/",
        }));
        const { editor } = await setupEditor(`<p>abc</p><p>[]<br></p>`);
        await insertText(editor, "/link");
        await animationFrame();
        await click(".o-we-command-name:first");
        await contains(".o-we-linkpopover input.o_we_href_input_link").fill("http://odoo.com/");
        await animationFrame();
        expect("button.o_we_replace_title_btn").toHaveCount(1);
        expect("a.o_we_replace_title_btn").toHaveCount(0);
        const pNode = document.querySelector("p");
        setSelection({
            anchorNode: pNode,
            anchorOffset: 0,
        });
        await expectElementCount(".o-we-linkpopover", 0);
        const link = document.querySelector("a");
        setSelection({
            anchorNode: link,
            anchorOffset: 0,
        });
        await waitFor(".o_we_replace_title_btn");
        await expectElementCount(".o-we-linkpopover", 1);
        expect("a.o_we_replace_title_btn").toHaveCount(1);
        expect("button.o_we_replace_title_btn").toHaveCount(0);
    });
});

describe("link in templates", () => {
    test("Should not remove a link with t-attf-href", async () => {
        const { el } = await setupEditor('<p>test<a t-attf-href="/test/1">li[]nk</a></p>');

        await expectElementCount(".o-we-linkpopover", 1);
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

        await expectElementCount(".o-we-linkpopover", 1);
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
});

describe("readonly mode", () => {
    test("popover should not display edit buttons in readonly mode", async () => {
        await setupEditor('<p><a class="o_link_readonly" href="http://test.test/">link[]</a></p>');
        await waitFor(".o-we-linkpopover");
        // Copy link button should be available
        expect(".o-we-linkpopover .o_we_copy_link").toHaveCount(1);
        // Edit and unlink buttons should not be available
        expect(".o-we-linkpopover .o_we_edit_link").toHaveCount(0);
        expect(".o-we-linkpopover .o_we_remove_link").toHaveCount(0);
    });
    // TODO: need to check with AGE
    test.todo("popover should not open for not editable image", async () => {
        await setupEditor(`<a href="#"><img src="${base64Img}" contenteditable="false"></a>`);
        await click("img");
        await animationFrame();
        await expectElementCount(".o-we-linkpopover", 0);
    });
});

describe("link in contenteditable=false", () => {
    test("popover should not display remove button if link is in a contenteditable=false", async () => {
        await setupEditor(
            '<p contenteditable="false"><a contenteditable="true" href="http://test.test/">link[]</a></p>'
        );
        await waitFor(".o-we-linkpopover");
        // Copy and edit link button should be available
        expect(".o-we-linkpopover .o_we_copy_link").toHaveCount(1);
        expect(".o-we-linkpopover .o_we_edit_link").toHaveCount(1);
        // Unlink buttons should not be available
        expect(".o-we-linkpopover .o_we_remove_link").toHaveCount(0);
    });
    test("toolbar should not display unlink button if link is in a contenteditable=false", async () => {
        await setupEditor(
            '<p contenteditable="false"><a contenteditable="true" href="http://test.test/">l[in]k</a></p>'
        );
        await waitFor(".o-we-toolbar");
        // Link button should be available and active
        expect(".o-we-toolbar button.active .fa-link").toHaveCount(1);
        // Unlink button should not be available
        expect(".o-we-toolbar .fa-unlink").toHaveCount(0);
    });
});

describe("upload file via link popover", () => {
    test("should display upload button when url input is empty", async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", {
            config: { Plugins: [...MAIN_PLUGINS, ...NO_EMBEDDED_COMPONENTS_FALLBACK_PLUGINS] },
        });
        execCommand(editor, "openLinkTools");
        await waitFor(".o-we-linkpopover");
        // Upload button should be visible
        expect("button i[class='fa fa-upload']").toHaveCount(1);
        await click(".o_we_href_input_link");
        await press("a");
        await animationFrame();
        // Upload button should NOT be visible
        expect("button i[class='fa fa-upload']").toHaveCount(0);
        await press("Backspace");
        await animationFrame();
        // Upload button should be visible again
        expect("button i[class='fa fa-upload']").toHaveCount(1);
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
        const { editor, el } = await setupEditor("<p>[]<br></p>", {
            config: { Plugins: [...MAIN_PLUGINS, ...NO_EMBEDDED_COMPONENTS_FALLBACK_PLUGINS] },
        });
        const mockedUpload = patchUpload(editor);
        execCommand(editor, "openLinkTools");
        await waitFor(".o-we-linkpopover");
        await click("button i[class='fa fa-upload']");
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
            `<p><a href="${expectedUrl}" data-attachment-id="1">file.txt[]</a></p>`
        );
    });

    test("direct download option works as expected", async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", {
            config: { allowTargetBlank: true },
        });
        execCommand(editor, "openLinkTools");
        await contains("input.o_we_href_input_link").fill(
            "/web/content/1?unique=123&download=true",
            { confirm: false }
        );
        expect(".direct-download-option input").toBeChecked();

        await contains("input.o_we_href_input_link").edit("/web/content/1?unique=123", {
            confirm: false,
        });
        expect(".direct-download-option input").not.toBeChecked();

        await contains(".direct-download-option input").check();
        expect("input.o_we_href_input_link").toHaveValue("/web/content/1?unique=123&download=true");

        await contains(".direct-download-option input").uncheck();
        expect("input.o_we_href_input_link").toHaveValue("/web/content/1?unique=123");
    });

    test("label input does not get filled on file upload if it is already filled", async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", {
            config: { Plugins: [...MAIN_PLUGINS, ...NO_EMBEDDED_COMPONENTS_FALLBACK_PLUGINS] },
        });
        const mockedUpload = patchUpload(editor);
        execCommand(editor, "openLinkTools");
        await waitFor(".o-we-linkpopover");
        // Fill label input
        await contains(".o-we-linkpopover input.o_we_label_link").fill("label");
        // Upload a file
        await click("button i[class='fa fa-upload']");
        await mockedUpload;
        await animationFrame();
        // Label remains unchanged
        expect(".o_we_label_link").toHaveValue("label");
    });

    test("popover in preview mode should display the file's mimetype as favicon", async () => {
        onRpc("ir.attachment", "read", () => [{ name: "file.txt", mimetype: "text/plain" }]);
        await setupEditor(
            '<p><a href="/web/content/1?download=true&unique=123">file.txt[]</a></p>'
        );
        const favIcon = await waitFor(".o_we_preview_favicon span.o_image");
        expect(favIcon).toHaveAttribute("data-mimetype", "text/plain");
    });
});

describe("apply button should be disabled when the URL is empty", () => {
    test("when URL on link is empty, the apply link button should be disabled (1)", async () => {
        await setupEditor("<p>this is a <a>li[]nk</a></p>");
        await waitFor(".o-we-linkpopover");
        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("");
        await tick();
        expect(".o_we_apply_link").toHaveAttribute("disabled");
    });
    test("when URL on link is empty, the apply link button should be disabled (2)", async () => {
        await setupEditor('<p>this is a <a href="">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("");
        await tick();
        expect(".o_we_apply_link").toHaveAttribute("disabled");
    });
    test("when URL on link is empty, the apply link button should be disabled (3)", async () => {
        await setupEditor('<p>this is a <a href="http://test.test/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await contains(".o-we-linkpopover input.o_we_href_input_link").edit("");
        await tick();
        expect(".o_we_apply_link").toHaveAttribute("disabled");
    });
    test("when edit a link's label and URL to '', the apply link button should be disabled", async () => {
        await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await contains(".o-we-linkpopover input.o_we_label_link").clear();
        await contains(".o-we-linkpopover input.o_we_href_input_link").clear();
        await tick();
        expect(".o_we_apply_link").toHaveAttribute("disabled");
    });
});

describe("hidden label field", () => {
    test("label field should be hidden if <a> content is not text only", async () => {
        await setupEditor(`<p><a href="http://test.com/"><img src="${base64Img}">te[]xt</a></p>`);
        await expectElementCount(".o-we-linkpopover", 1);
        // open edit mode and check if label input is hidden
        await click(".o_we_edit_link");
        await waitFor(".o_we_href_input_link", { timeout: 1500 });
        expect(".o_we_label_link").not.toBeVisible();
        expect(".o_we_href_input_link").toHaveValue("http://test.com/");
    });
});

describe("link popover with empty URL", () => {
    test("should not close the popover when pressing Enter with an empty URL", async () => {
        const { editor } = await setupEditor("<p>ab[]</p>");
        await insertText(editor, "/link");
        await animationFrame();
        expect(".active .o-we-command-name").toHaveText("Link");
        await click(".o-we-command-name:first");
        await expectElementCount(".o-we-linkpopover", 1);
        await contains(".o-we-linkpopover input.o_we_label_link").fill("label");
        await click(".o-we-linkpopover input.o_we_href_input_link");
        await press("Enter");
        await animationFrame();
        await expectElementCount(".o-we-linkpopover", 1);
    });
    test("should close the popover and create a link with href '#' when URL is empty and clicking outside", async () => {
        const { editor, el } = await setupEditor("<p>ab[]</p>");
        await insertText(editor, "/link");
        await animationFrame();
        expect(".active .o-we-command-name").toHaveText("Link");
        await click(".o-we-command-name:first");
        await expectElementCount(".o-we-linkpopover", 1);
        await contains(".o-we-linkpopover input.o_we_label_link").fill("label");
        queryOne(".o_we_href_input_link").focus();
        await fill("http://test.com/");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>ab<a href="http://test.com/">label</a></p>'
        );
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
        expect(getContent(el)).toBe('<p>[]ab\ufeff<a href="#">\ufefflabel\ufeff</a>\ufeff</p>');
    });
    test("should close the popover and fallback href to '#' on empty URL when clicking outside", async () => {
        const { el } = await setupEditor("<p>[abc]</p>");
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-link");
        await waitFor(".o-we-linkpopover");
        expect(".o-we-linkpopover input.o_we_label_link").toHaveValue("abc");
        await fill("d"); // Change label value
        expect(".o-we-linkpopover input.o_we_label_link").toHaveValue("abcd");
        queryOne(".o_we_href_input_link").focus();
        await fill("http://test.com/");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.com/">abcd</a></p>'
        );
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
        expect(getContent(el)).toBe('<p>[]\ufeff<a href="#">\ufeffabcd\ufeff</a>\ufeff</p>');
    });
    test("when edit a link URL to '', and clicking outside the link popover should set href to '#'", async () => {
        const { el } = await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
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
        expect(cleanLinkArtifacts(getContent(el))).toBe('<p>[]this is a <a href="#">link</a></p>');
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
});

describe("label is a valid URL", () => {
    test("URL input should be prefilled by corresponding URL if the label matches the URL format", async () => {
        const { el } = await setupEditor("<p>[google.com]</p>");
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-link");
        await waitFor(".o-we-linkpopover");
        expect("input.o_we_label_link").toHaveValue("google.com");
        expect("input.o_we_href_input_link").toHaveValue("https://google.com");
        await click(".o_we_apply_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="https://google.com">google.com[]</a></p>'
        );
    });
    test("URL input should be prefilled by corresponding URL if the label matches the URL format (2)", async () => {
        const { el } = await setupEditor("<p>[https://google.com]</p>");
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-link");
        await waitFor(".o-we-linkpopover");
        expect("input.o_we_label_link").toHaveValue("https://google.com");
        expect("input.o_we_href_input_link").toHaveValue("https://google.com");
        await click(".o_we_apply_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="https://google.com">https://google.com[]</a></p>'
        );
    });
    test("URL input should be prefilled by corresponding URL if the label matches the email format", async () => {
        const { el } = await setupEditor("<p>[test@test.com]</p>");
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-link");
        await waitFor(".o-we-linkpopover");
        expect("input.o_we_label_link").toHaveValue("test@test.com");
        expect("input.o_we_href_input_link").toHaveValue("mailto:test@test.com");
        await click(".o_we_apply_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="mailto:test@test.com">test@test.com[]</a></p>'
        );
    });
    test("URL input should be prefilled by corresponding URL if the label matches the email format (2)", async () => {
        const { el } = await setupEditor("<p>[mailto:test@test.com]</p>");
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-link");
        await waitFor(".o-we-linkpopover");
        expect("input.o_we_label_link").toHaveValue("mailto:test@test.com");
        expect("input.o_we_href_input_link").toHaveValue("mailto:test@test.com");
        await click(".o_we_apply_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="mailto:test@test.com">mailto:test@test.com[]</a></p>'
        );
    });
    test("URL input should be prefilled by corresponding URL if the label matches the telephone format", async () => {
        const { el } = await setupEditor("<p>[12345678]</p>");
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-link");
        await waitFor(".o-we-linkpopover");
        expect("input.o_we_label_link").toHaveValue("12345678");
        expect("input.o_we_href_input_link").toHaveValue("tel:12345678");
        await click(".o_we_apply_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="tel:12345678">12345678[]</a></p>'
        );
    });
    test("URL input should be prefilled by corresponding URL if the label matches the telephone format (2)", async () => {
        const { el } = await setupEditor("<p>[tel:123]</p>");
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-link");
        await waitFor(".o-we-linkpopover");
        expect("input.o_we_label_link").toHaveValue("tel:123");
        expect("input.o_we_href_input_link").toHaveValue("tel:123");
        await click(".o_we_apply_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe('<p><a href="tel:123">tel:123[]</a></p>');
    });
    test("popover should display href URL even if label is a valid URL and differs from href", async () => {
        await setupEditor('<p><a href="https://odoo.com/">googl[]e.com</a></p>');
        await waitFor(".o-we-linkpopover", { timeout: 1500 });
        expect(queryFirst(".o-we-linkpopover a").href).toBe("https://odoo.com/");
        await click(".o_we_edit_link");
        await waitFor(".o_we_href_input_link");
        expect("input.o_we_href_input_link").toHaveValue("https://odoo.com/");
    });
});
