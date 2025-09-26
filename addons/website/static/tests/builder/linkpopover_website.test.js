import { expect, test } from "@odoo/hoot";
import { click, press, waitFor, waitForNone, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { cleanLinkArtifacts } from "@html_editor/../tests/_helpers/format";
import { getContent, setContent, setSelection } from "@html_editor/../tests/_helpers/selection";
import { base64Img, setupEditor } from "@html_editor/../tests/_helpers/editor";
import { contains, onRpc, serverState, patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    click as mailClick,
    mailModels,
    openFormView,
    start,
} from "@mail/../tests/mail_test_helpers";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { HtmlField } from "@html_editor/fields/html_field";
import { browser } from "@web/core/browser/browser";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("autocomplete should shown and able to edit the link", async () => {
    onRpc("/website/get_suggested_links", () => {
        expect.step("/website/get_suggested_links");
        return {
            matching_pages: [
                {
                    value: "/contactus",
                    label: "/contactus (Contact Us)",
                },
            ],
            others: [
                {
                    title: "Apps url",
                    values: [
                        {
                            value: "/contactus",
                            icon: "/website/static/description/icon.png",
                            label: "/contactus (Contact Us)",
                        },
                    ],
                },
            ],
        };
    });
    onRpc("/contactus", () => ({}));
    onRpc("/html_editor/link_preview_internal", () => ({}));

    const { el } = await setupEditor('<p>this is a <a href="http://test.com/">li[]nk</a></p>');

    await waitFor(".o-we-linkpopover");
    await click(".o_we_edit_link");
    await animationFrame();
    // the url input should be autocomplete
    await contains(".o-autocomplete--input").focus();

    // autocomplete dropdown should be there
    await press(["ctrl", "a"]);
    await press("c");
    // Should update preview with typed URL.
    expect(cleanLinkArtifacts(getContent(el))).toBe('<p>this is a <a href="c">link</a></p>');
    await waitFor(".o-autocomplete--dropdown-menu", { timeout: 3000 });
    expect.verifySteps(["/website/get_suggested_links"]);

    expect(".ui-autocomplete-category").toHaveCount(1);
    expect(".o-autocomplete--dropdown-item img").toHaveCount(1);

    await click(".o-autocomplete--dropdown-item:first");
    // Should update preview with selected item.
    expect(cleanLinkArtifacts(getContent(el))).toBe(
        '<p>this is a <a href="/contactus">link</a></p>'
    );
    await click(".o_we_apply_link");
    // the url should be applied after selecting a dropdown item
    expect(cleanLinkArtifacts(getContent(el))).toBe(
        '<p>this is a <a href="/contactus">li[]nk</a></p>'
    );

    await waitFor(".o_we_edit_link");
    await click(".o_we_edit_link");
    await animationFrame();
    await contains(".o-autocomplete--input").focus();

    await press(["ctrl", "a"]);
    await press("#");
    await waitFor(".o-autocomplete--dropdown-menu", { timeout: 3000 });
    // check the default page anchors are in the autocomplete dropdown
    expect(".o-autocomplete--dropdown-item:first").toHaveText("#top");
    expect(".o-autocomplete--dropdown-item:last").toHaveText("#bottom");
});

test("autocomplete suggestions for image links don’t update preview until applied", async () => {
    onRpc("/website/get_suggested_links", () => {
        expect.step("/website/get_suggested_links");
        return {
            matching_pages: [
                {
                    value: "/contactus",
                    label: "/contactus (Contact Us)",
                },
            ],
            others: [
                {
                    title: "Apps url",
                    values: [
                        {
                            value: "/contactus",
                            icon: "/website/static/description/icon.png",
                            label: "/contactus (Contact Us)",
                        },
                    ],
                },
            ],
        };
    });
    onRpc("/contactus", () => ({}));
    onRpc("/html_editor/link_preview_internal", () => ({}));

    const { el } = await setupEditor(
        `<p><a href="http://test.test/">[<img src="${base64Img}">]</a></p>`
    );

    await waitFor(".o-we-linkpopover");
    await click(".o_we_edit_link");
    await animationFrame();
    // the url input should be autocomplete
    await contains(".o-autocomplete--input").focus();

    // autocomplete dropdown should be there
    await press(["ctrl", "a"]);
    await press("c");
    // typing URL shouldn’t change image link preview.
    expect(getContent(el)).toBe(`<p><a href="http://test.test/"><img src="${base64Img}"></a></p>`);
    await waitFor(".o-autocomplete--dropdown-menu", { timeout: 3000 });
    expect.verifySteps(["/website/get_suggested_links"]);

    expect(".ui-autocomplete-category").toHaveCount(1);
    expect(".o-autocomplete--dropdown-item img").toHaveCount(1);

    await click(".o-autocomplete--dropdown-item:first");
    // selecting suggestion shouldn’t change image link preview.
    expect(getContent(el)).toBe(`<p><a href="http://test.test/"><img src="${base64Img}"></a></p>`);
    await click(".o_we_apply_link");
    // the url should be applied after selecting a dropdown item
    expect(getContent(el)).toBe(`<p><a href="/contactus">[<img src="${base64Img}">]</a></p>`);
});

test("LinkPopover opens in full composer", async () => {
    let htmlEditor;
    mailModels.MailComposeMessage._views = {
        "form,false": `
        <form js_class="mail_composer_form">
            <field name="body" type="html" widget="html_composer_message"/>
        </form>`,
    };
    patchWithCleanup(HtmlField.prototype, {
        onEditorLoad(editor) {
            htmlEditor = editor;
            return super.onEditorLoad(...arguments);
        },
    });
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await mailClick("button", { text: "Log note" });
    await mailClick("button[title='Open Full Composer']");
    await waitFor(".odoo-editor-editable");
    htmlEditor.editable.focus();
    await insertText(htmlEditor, "test");
    const node = queryOne(".odoo-editor-editable div");
    setSelection({ anchorNode: node, anchorOffset: 0, focusNode: node, focusOffset: 1 });
    await mailClick(".o-we-toolbar .fa-link");
    await waitFor(".o-we-linkpopover");
    await animationFrame();
    expect(".o-we-linkpopover").toHaveCount(1);
});

test("link redirection should be prefixed for url of website pages only", async () => {
    patchWithCleanup(browser, {
        open(url) {
            expect.step("website page url prefixed");
            expect(url.pathname.startsWith("/@")).toBe(true);
        },
    });
    onRpc("/html_editor/link_preview_internal", () => ({}));
    onRpc("/contactus", () => ({}));
    onRpc("/odoo/project/1", () => ({}));
    onRpc("/web/project/1", () => ({}));

    // website pages should be prefixed with /@
    const { el } = await setupEditor('<p>this is a <a href="/contactus">li[]nk</a></p>');
    await waitFor(".o-we-linkpopover");
    await click(".o-we-linkpopover a");
    expect.verifySteps(["website page url prefixed"]);

    // other backend urls and external urls should not be prefixed
    setContent(el, `<p>this is a[] <a href="/odoo/project/1">link</a></p>`);
    await waitForNone(".o-we-linkpopover");
    setContent(el, `<p>this is a <a href="/odoo/project/1">li[]nk</a></p>`);
    await waitFor(".o-we-linkpopover");
    await click(".o-we-linkpopover a");
    expect.verifySteps([]);

    setContent(el, `<p>this is a[] <a href="/web/project/1">link</a></p>`);
    await waitForNone(".o-we-linkpopover");
    setContent(el, `<p>this is a <a href="/web/project/1">li[]nk</a></p>`);
    await waitFor(".o-we-linkpopover");
    await click(".o-we-linkpopover a");
    expect.verifySteps([]);

    setContent(el, `<p>this is a[] <a href="http://test.test">link</a></p>`);
    await waitForNone(".o-we-linkpopover");
    setContent(el, `<p>this is a <a href="http://test.test">li[]nk</a></p>`);
    await waitFor(".o-we-linkpopover");
    await click(".o-we-linkpopover a");
    expect.verifySteps([]);
});
test("should open seo advanced popup when gear icon is clicked", async () => {
    await setupWebsiteBuilder(`
        <div id="wrapwrap">
            <p>this is a <a href="http://test.com/">link</a></p>
        </div>
    `);
    const linkText = queryOne(":iframe #wrapwrap a");
    setSelection({
        anchorNode: linkText.firstChild,
        anchorOffset: 1,
    });
    await waitFor(".o-we-linkpopover");
    await contains(".o_we_edit_link").click();
    await waitFor(".o_we_href_input_link");
    await contains(".o_we_href_input_link").click();
    await contains(".o-we-linkpopover .fa-gear").click();
    expect(".o_advance_option_panel").toHaveCount(1);
    expect(".o_advance_option_panel .o_seo_option_row").toHaveCount(4);
});
test("should add rel='nofollow' when checkbox is selected and applied", async () => {
    await setupWebsiteBuilder(`
        <div id="wrapwrap">
            <p>this is a <a href="http://test.com/">link</a></p>
        </div>
    `);
    const linkText = queryOne(":iframe #wrapwrap a");
    setSelection({
        anchorNode: linkText.firstChild,
        anchorOffset: 1,
    });
    await waitFor(".o-we-linkpopover");
    await contains(".o_we_edit_link").click();
    await waitFor(".o_we_href_input_link");
    await contains(".o_we_href_input_link").click();
    await contains(".o-we-linkpopover .fa-gear").click();
    expect(".o_advance_option_panel").toHaveCount(1);
    await contains(".o_seo_option_row:nth-of-type(1) input[type='checkbox']").click();
    await contains(".o_advance_option_panel .fa-angle-left").click();
    await waitFor(".o-we-linkpopover");
    await contains(".o_we_apply_link").click();
    expect(linkText).toHaveAttribute("rel", "nofollow");
});
test("should add multipule relAttribute in anchor tag when checkbox is selected and applied", async () => {
    await setupWebsiteBuilder(`
        <div id="wrapwrap">
            <p>this is a <a href="http://test.com/">link</a></p>
        </div>
    `);
    const linkText = queryOne(":iframe #wrapwrap a");
    setSelection({
        anchorNode: linkText.firstChild,
        anchorOffset: 1,
    });
    await waitFor(".o-we-linkpopover");
    await contains(".o_we_edit_link").click();
    await waitFor(".o_we_href_input_link");
    await contains(".o_we_href_input_link").click();
    await contains(".o-we-linkpopover .fa-gear").click();
    expect(".o_advance_option_panel").toHaveCount(1);
    await contains(".o_seo_option_row:nth-of-type(1) input[type='checkbox']").click();
    await contains(".o_seo_option_row:nth-of-type(2) input[type='checkbox']").click();
    await contains(".o_seo_option_row:nth-of-type(3) input[type='checkbox']").click();
    await contains(".o_advance_option_panel .fa-angle-left").click();
    await waitFor(".o-we-linkpopover");
    await contains(".o_we_apply_link").click();
    expect(linkText).toHaveAttribute("rel", "nofollow noreferrer sponsored");
});
test("should add _blank attribute on open in a new window is checked", async () => {
    await setupWebsiteBuilder(`
        <div id="wrapwrap">
            <p>this is a <a href="http://test.com/">link</a></p>
        </div>
    `);
    const linkText = queryOne(":iframe #wrapwrap a");
    setSelection({
        anchorNode: linkText.firstChild,
        anchorOffset: 1,
    });
    await waitFor(".o-we-linkpopover");
    await contains(".o_we_edit_link").click();
    await waitFor(".o_we_href_input_link");
    await contains(".o_we_href_input_link").click();
    await contains(".o-we-linkpopover .fa-gear").click();
    expect(".o_advance_option_panel").toHaveCount(1);
    await contains(".o_advance_option_panel .target-blank-option").click();
    await contains(".o_seo_option_row:nth-of-type(5) input[type='checkbox']").click();
    await click(".o_advance_option_panel .fa-angle-left");
    await waitFor(".o-we-linkpopover");
    await contains(".o_we_apply_link").click();
    expect(linkText).toHaveAttribute("target", "_blank");
    expect(linkText).toHaveAttribute("rel", "noopener");
});

test("should allow target _blank on custom button", async () => {
    const { getEditor } = await setupWebsiteBuilder(`
        <div id="wrapwrap">
            <p>Hello</p>
        </div>
    `);
    const editor = getEditor();
    const linkText = editor.editable.querySelector("p");
    setSelection({
        anchorNode: linkText.firstChild,
        anchorOffset: 0,
        focusOffset: 5,
    });
    await waitFor(".o-we-toolbar");
    await click(".o-we-toolbar .fa-link");
    await waitFor(".o_we_href_input_link");
    await contains(".o_we_href_input_link").click();
    await contains(".o-we-linkpopover input.o_we_href_input_link").edit("http://test.test/", {
        confirm: false,
    });
    await contains(".o-we-linkpopover .fa-gear").click();
    expect(".o_advance_option_panel").toHaveCount(1);
    await contains(".o_advance_option_panel .target-blank-option").click();
    await click(".o_advance_option_panel .fa-angle-left");
    await waitFor(".o-we-linkpopover");
    await contains(".o_we_apply_link").click();
    const anchor = editor.editable.querySelector("a");
    expect(anchor).toHaveAttribute("target", "_blank");
});

test("link redirection should not be prefixed when the current page is not a website page", async () => {
    patchWithCleanup(browser, {
        open(url) {
            expect.step("website page url prefixed");
            expect(url.pathname.startsWith("/@")).toBe(true);
        },
        location: {
            // simulating being on a non-website page (eg. backend) by using /odoo/ URL
            href: browser.location.origin + "/odoo/contactus",
            hostname: browser.location.hostname,
        },
    });
    onRpc("/html_editor/link_preview_internal", () => ({}));
    onRpc("/contactus", () => ({}));

    // website pages should not be prefixed with /@
    await setupEditor('<p>this is a <a href="/contactus">li[]nk</a></p>');
    await waitFor(".o-we-linkpopover");
    await click(".o-we-linkpopover a");
    // the open method should not be called from onClickForcePreviewMode
    expect.verifySteps([]);
});

test("Focus should be on label when adding a new URL", async () => {
    const { editor } = await setupEditor("<p>ab[]</p>");
    await insertText(editor, "/link");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("Link");
    await click(".o-we-command-name:first");
    await animationFrame();
    expect(".o-we-linkpopover").toHaveCount(1);
    expect(".o-we-linkpopover input.o_we_label_link").toBeFocused({
        message: "should focus label input by default",
    });
});
