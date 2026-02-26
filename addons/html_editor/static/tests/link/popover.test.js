import { describe, expect, test } from "@odoo/hoot";
import { click, fill, press, queryFirst, queryOne, waitFor, waitForNone } from "@odoo/hoot-dom";
import { animationFrame, tick } from "@odoo/hoot-mock";
import { markup } from "@odoo/owl";
import { contains, dataURItoBlob, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupEditor } from "../_helpers/editor";
import { cleanLinkArtifacts } from "../_helpers/format";
import { getContent, setContent, setSelection } from "../_helpers/selection";
import { expectElementCount } from "../_helpers/ui_expectations";
import { insertText } from "../_helpers/user_actions";
import { execCommand } from "../_helpers/userCommands";
import { MAIN_PLUGINS, NO_EMBEDDED_COMPONENTS_FALLBACK_PLUGINS } from "@html_editor/plugin_sets";

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
        expect(".o_we_edit_link").toHaveCount(1);
    });
    test("link popover shows remove button when editing a link", async () => {
        await setupEditor(`<p>this is a <a href="http://test.com/">li[]nk</a></p>`);
        await expectElementCount(".o-we-linkpopover", 1);
        await click(".o_we_edit_link");
        await animationFrame();
        expect(".o_we_remove_link").toHaveCount(1);
    });
    test("link popover should not have the remove button when link is unremovable", async () => {
        await setupEditor('<p>a<a class="oe_unremovable" href="http://test.test/">bcd[]</a>e</p>');
        await expectElementCount(".o-we-linkpopover", 1);
        await click(".o_we_edit_link");
        await animationFrame();
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

describe("popover should not reposition when editing", () => {
    test("when editing the link url, the popover should not reposition", async () => {
        const { el } = await setupEditor("<p>H[ell]o</p>");
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-link");
        await animationFrame();
        await waitFor(".o-we-linkpopover");
        const popoverEl = queryOne(".o-we-linkpopover").parentElement;
        const initialPopoverBox = popoverEl.getBoundingClientRect();

        queryOne(".o-we-linkpopover input.o_we_href_input_link").focus();
        await fill("test.com");
        await animationFrame();
        const newPopoverBox = popoverEl.getBoundingClientRect();

        expect(Math.floor(newPopoverBox.top)).toBe(Math.floor(initialPopoverBox.top));
        expect(Math.floor(newPopoverBox.left)).toBe(Math.floor(initialPopoverBox.left));

        await waitFor(".o_we_apply_link:not([disabled])");
        await click(".o_we_apply_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>H<a href="https://test.com">ell[]</a>o</p>'
        );
    });
    test("In iframe, when editing the link url, the popover should not reposition", async () => {
        const { el } = await setupEditor("<p>H[ell]o</p>", { props: { iframe: true } });
        await waitFor(".o-we-toolbar");
        await click(".o-we-toolbar .fa-link");
        await animationFrame();
        await waitFor(".o-we-linkpopover");
        const popoverEl = queryOne(".o-we-linkpopover").parentElement;
        const initialPopoverBox = popoverEl.getBoundingClientRect();

        queryOne(".o-we-linkpopover input.o_we_href_input_link").focus();
        await fill("test.com");
        await animationFrame();
        const newPopoverBox = popoverEl.getBoundingClientRect();

        expect(Math.floor(newPopoverBox.top)).toBe(Math.floor(initialPopoverBox.top));
        expect(Math.floor(newPopoverBox.left)).toBe(Math.floor(initialPopoverBox.left));

        await waitFor(".o_we_apply_link:not([disabled])");
        await click(".o_we_apply_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p>H<a href="https://test.com">ell[]</a>o</p>'
        );
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
    test("after clicking on apply button, the popover should be with the non editing mode, e.g. edit button", async () => {
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
        expect(".o_we_edit_link").toHaveCount(1);
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
        await click(".o_we_edit_link");
        await animationFrame();
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
    test("should trap focus within link popover when using Tab and Shift+Tab", async () => {
        await setupEditor(`<p><a>li[]nk</a></p>`);
        await expectElementCount(".o-we-linkpopover", 1);

        await animationFrame();
        expect(".o_we_href_input_link").toBeFocused();
        // Tab through all focusable elements
        await press("Tab");
        await animationFrame();
        expect("button[name='link_type']").toBeFocused();
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
});

describe("popover should show link preview", () => {
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
    test("test internal image link preview", async () => {
        const base64Image =
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII=";
        const url = "/web/image/hoot.png";
        onRpc(
            url,
            () =>
                new Response(dataURItoBlob(base64Image), {
                    headers: {
                        "Content-Type": "image/png",
                    },
                })
        );
        const { editor } = await setupEditor(`<p>[]<br></p>`);
        await insertText(editor, "/link");
        await animationFrame();
        await click(".o-we-command-name:first");
        await contains(".o-we-linkpopover input.o_we_href_input_link").fill(url);
        await animationFrame();

        expect(".o_we_preview_favicon .fa-picture-o").toHaveCount(1);
        expect(`a.o_we_url_link[href='${url}']`).toHaveText(url);
        expect(".o_we_replace_title_btn").toHaveCount(1);
        expect(`.o_extra_info_card a[href='${url}'] img[src^='data:']`).toHaveCount(1);
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
    test("should open same-page links with anchor in current tab", async () => {
        onRpc("/html_editor/link_preview_internal", () => ({}));
        onRpc("/", () => ({}));
        await setupEditor(`<p>This is a <a href="${window.origin}/#section">li[]nk</a></p>`);
        await waitFor(".o-we-linkpopover");
        expect(".o-we-linkpopover .o_we_url_link").toHaveAttribute("target", "_self");
    });
    test("should open same-page links without anchor in new tab", async () => {
        onRpc("/html_editor/link_preview_internal", () => ({}));
        onRpc("/section", () => ({}));
        await setupEditor(`<p>This is a <a href="${window.origin}/section">li[]nk</a></p>`);
        await waitFor(".o-we-linkpopover");
        expect(".o-we-linkpopover .o_we_url_link").toHaveAttribute("target", "_blank");
    });
    test("Should not show link preview when selection in input/textarea", async () => {
        await setupEditor(
            `<p><a href="http://test.com/">a[]b</a><span contenteditable="false" data-oe-protected="true"><input></span></p>`
        );
        await waitFor(".o-we-linkpopover");
        queryOne("input").focus();
        await expectElementCount(".o-we-linkpopover", 0);
    });
});

describe("popover in contenteditable=false or readonly mode", () => {
    test("popover should not display edit buttons in readonly mode", async () => {
        await setupEditor('<p><a class="o_link_readonly" href="http://test.test/">link[]</a></p>');
        await waitFor(".o-we-linkpopover");
        // Edit button should not be available.
        expect(".o-we-linkpopover .o_we_edit_link").toHaveCount(0);
    });
    test("popover should not display remove button if link is in a contenteditable=false", async () => {
        await setupEditor(
            '<p contenteditable="false"><a contenteditable="true" href="http://test.test/">link[]</a></p>'
        );
        await waitFor(".o-we-linkpopover");
        // Edit link button should be available
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

describe("popover for file uploads", () => {
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

describe("popover with empty URL", () => {
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
        expect(".o-we-linkpopover input.o_we_href_input_link").toBeFocused();
        await fill("http://test.com/");
        queryOne(".o_we_label_link").focus();
        expect(".o-we-linkpopover input.o_we_label_link").toHaveValue("abc");
        await fill("d"); // Change label value
        expect(".o-we-linkpopover input.o_we_label_link").toHaveValue("abcd");
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

describe("popover with a valid URL as label", () => {
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
    test("Focus should be on URL [label] when editing an existing link", async () => {
        await setupEditor(`<p>this is a <a href="http://test.com/">li[]nk</a></p>`);
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        expect(".o-we-linkpopover").toHaveCount(1);
        await animationFrame();
        expect(".o-we-linkpopover input.o_we_label_link").toBeFocused({
            message: "should focus label input by default, when we don't have a label",
        });
    });
});
