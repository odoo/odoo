import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { setContent, getContent, setSelection } from "../_helpers/selection";
import { setupEditor } from "../_helpers/editor";
import { waitUntil, waitFor, click, queryOne, press } from "@odoo/hoot-dom";
import { browser } from "@web/core/browser/browser";
import { insertText } from "../_helpers/user_actions";

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
        expect(getContent(el)).toBe('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
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
        await waitFor(".o_we_href_input_link");
        queryOne(".o_we_href_input_link").focus();
        // mimic the link input behavior
        for (const char of "http://test.com/") {
            press(char);
        }
        await waitFor(".o_we_apply_link");
        click(".o_we_apply_link");
        expect(getContent(el)).toBe('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
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
        await waitFor(".o_we_apply_link");
        queryOne(".o_we_label_link").focus();
        // mimic the link input behavior
        for (const char of "new") {
            press(char);
        }
        click(".o_we_apply_link");
        expect(getContent(el)).toBe('<p>this is a <a href="http://test.com/">linknew[]</a></p>');
    });
    test("when the label is empty, it should be set as the URL", async () => {
        const { el } = await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        click(".o_we_edit_link");
        await waitFor(".o_we_apply_link");
        await animationFrame();
        queryOne(".o_we_label_link").focus();
        // mimic the link input behavior
        for (let i = 0; i < el.textContent.length; i++) {
            press("Backspace");
        }
        click(".o_we_apply_link");
        expect(getContent(el)).toBe(
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
        const { el } = await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        click(".o_we_edit_link");
        await animationFrame();
        queryOne(".o_we_label_link").focus();
        const linkEl = queryOne("a");
        // mimic the link input behavior
        for (let i = 0; i < linkEl.textContent.length; i++) {
            press("Backspace");
        }
        queryOne(".o_we_href_input_link").focus();
        // mimic the link input behavior
        for (let i = 0; i < linkEl.href.length; i++) {
            press("Backspace");
        }
        click(".o_we_apply_link");
        await animationFrame();
        expect(getContent(el)).toBe("<p>this is a []</p>");
    });
});

describe("Incorrect URL should be corrected", () => {
    test("when edit a link's URL to 'test.com', the link's URL should be corrected", async () => {
        const { el } = await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');
        await waitFor(".o-we-linkpopover");
        click(".o_we_edit_link");
        await animationFrame();
        queryOne(".o_we_label_link").focus();
        const linkEl = queryOne("a");

        queryOne(".o_we_href_input_link").focus();
        // mimic the link input behavior
        for (let i = 0; i < linkEl.href.length; i++) {
            press("Backspace");
        }
        for (const char of "newtest.com") {
            press(char);
        }
        click(".o_we_apply_link");
        await animationFrame();
        expect(getContent(el)).toBe('<p>this is a <a href="http://newtest.com">li[]nk</a></p>');
    });
    test("when a link's URL is an email, the link's URL should start with mailto:", async () => {
        const { el } = await setupEditor("<p>this is a <a>li[]nk</a></p>");
        await animationFrame();
        await waitFor(".o_we_href_input_link");

        queryOne(".o_we_href_input_link").focus();
        for (const char of "test@test.com") {
            press(char);
        }
        click(".o_we_apply_link");
        await animationFrame();
        expect(getContent(el)).toBe('<p>this is a <a href="mailto:test@test.com">li[]nk</a></p>');
    });
    test("when a link's URL is an phonenumber, the link's URL should start with tel://:", async () => {
        const { el } = await setupEditor("<p>this is a <a>li[]nk</a></p>");
        await waitFor(".o_we_href_input_link");
        await animationFrame();

        queryOne(".o_we_href_input_link").focus();
        for (const char of "+1234567890") {
            press(char);
        }
        click(".o_we_apply_link");
        await animationFrame();
        expect(getContent(el)).toBe('<p>this is a <a href="tel://+1234567890">li[]nk</a></p>');
    });
});

describe("Link creation by powerbox", () => {
    test("click on link command in powerbox should create a link element and open the linkpopover", async () => {
        const { editor, el } = await setupEditor("<p>ab[]</p>");
        insertText(editor, "/link");
        await animationFrame();
        expect(".active .o-we-command-name").toHaveText("Link");

        click(".o-we-command-name:first");
        expect(getContent(el)).toBe("<p>ab<a>[]</a></p>");
        await animationFrame();
        await waitFor(".o-we-linkpopover");
        expect(".o-we-linkpopover").toHaveCount(1);
    });

    test("when create a new link by powerbox and not input anything, the link should be removed", async () => {
        const { editor, el } = await setupEditor("<p>ab[]</p>");
        insertText(editor, "/link");
        await animationFrame();
        click(".o-we-command-name:first");
        await animationFrame();
        await waitFor(".o-we-linkpopover");
        expect(".o-we-linkpopover").toHaveCount(1);
        expect(getContent(el)).toBe("<p>ab<a>[]</a></p>");

        const pNode = queryOne("p");
        setSelection({
            anchorNode: pNode,
            anchorOffset: 0,
            focusNode: pNode,
            focusOffset: 0,
        });
        await animationFrame();
        expect(getContent(el)).toBe("<p>[]ab</p>");
    });
    test("when create a new link by powerbox and only input the URL, the link should be created with corrected URL", async () => {
        const { editor, el } = await setupEditor("<p>ab[]</p>");
        insertText(editor, "/link");
        await animationFrame();
        click(".o-we-command-name:first");
        await animationFrame();
        await waitFor(".o-we-linkpopover");

        queryOne(".o_we_href_input_link").focus();
        for (const char of "test.com") {
            press(char);
        }
        await waitFor(".o_we_apply_link");
        click(".o_we_apply_link");
        expect(getContent(el)).toBe('<p>ab<a href="http://test.com">test.com[]</a></p>');
    });
});
