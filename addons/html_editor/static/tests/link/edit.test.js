import { describe, expect, test } from "@odoo/hoot";
import { deleteBackward, insertLineBreak, insertText, undo } from "../_helpers/user_actions";
import { setupEditor, testEditor } from "../_helpers/editor";
import { animationFrame } from "@odoo/hoot-mock";

import { click, press, waitFor, queryOne, queryAll, waitForNone } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { cleanLinkArtifacts } from "../_helpers/format";
import { getContent, setSelection } from "../_helpers/selection";

import { expectElementCount } from "../_helpers/ui_expectations";

describe("edit directly in editable", () => {
    describe("range collapsed", () => {
        test("should not change the url when a link is not edited (1)", async () => {
            await testEditor({
                contentBefore: '<p>a<a href="https://google.co">google.com</a>b</p>',
                contentAfter: '<p>a<a href="https://google.co">google.com</a>b</p>',
            });
        });

        test("should not change the url when a link is not edited (2)", async () => {
            await testEditor({
                contentBefore:
                    '<p>a<a href="https://google.xx">google.com</a>b<a href="https://google.co">cd[]</a></p>',
                stepFunction: async (editor) => {
                    await insertText(editor, "e");
                },
                contentAfter:
                    '<p>a<a href="https://google.xx">google.com</a>b<a href="https://google.co">cde[]</a></p>',
            });
        });

        test("should change the url when the label change (1)", async () => {
            await testEditor({
                contentBefore: '<p>a<a href="https://google.co">google.co[]</a>b</p>',
                stepFunction: async (editor) => {
                    await insertText(editor, "m");
                },
                contentAfter: '<p>a<a href="https://google.com">google.com[]</a>b</p>',
            });
        });

        test("should change the url when the label change (2)", async () => {
            await testEditor({
                contentBefore: '<p>a<a href="https://gogle.com">go[]gle.com</a>b</p>',
                stepFunction: async (editor) => {
                    await insertText(editor, "o");
                },
                contentAfter: '<p>a<a href="https://google.com">goo[]gle.com</a>b</p>',
            });
        });

        test("should change the url when the label change (3)", async () => {
            await testEditor({
                contentBefore: '<p>a<a href="https://else.com">go[]gle.com</a>b</p>',
                stepFunction: async (editor) => {
                    await insertText(editor, "o");
                },
                contentAfter: '<p>a<a href="https://else.com">goo[]gle.com</a>b</p>',
            });
        });

        test("should change the url when the label change (4)", async () => {
            await testEditor({
                contentBefore: '<p>a<a href="https://else.com">http://go[]gle.com</a>b</p>',
                stepFunction: async (editor) => {
                    await insertText(editor, "o");
                },
                contentAfter: '<p>a<a href="https://else.com">http://goo[]gle.com</a>b</p>',
            });
        });

        test("should change the url when the label change (5)", async () => {
            await testEditor({
                contentBefore: '<p>a<a href="mailto:hello@moto.com">hello@moto[].com</a></p>',
                stepFunction: async (editor) => {
                    await insertText(editor, "r");
                },
                contentAfter: '<p>a<a href="mailto:hello@motor.com">hello@motor[].com</a></p>',
            });
        });

        test("should change the url when the label change, without changing the protocol (1)", async () => {
            await testEditor({
                contentBefore: '<p>a<a href="http://google.co">google.co[]</a>b</p>',
                stepFunction: async (editor) => {
                    await insertText(editor, "m");
                },
                contentAfter: '<p>a<a href="http://google.com">google.com[]</a>b</p>',
            });
        });

        test("should change the url when the label change, without changing the protocol (2)", async () => {
            await testEditor({
                contentBefore: '<p>a<a href="https://google.co">google.co[]</a>b</p>',
                stepFunction: async (editor) => {
                    await insertText(editor, "m");
                },
                contentAfter: '<p>a<a href="https://google.com">google.com[]</a>b</p>',
            });
        });

        test("should change the url when the label change, changing to the suitable protocol (1)", async () => {
            await testEditor({
                contentBefore: '<p>a<a href="http://hellomoto.com">hello[]moto.com</a></p>',
                stepFunction: async (editor) => {
                    await insertText(editor, "@");
                },
                contentAfter: '<p>a<a href="mailto:hello@moto.com">hello@[]moto.com</a></p>',
            });
        });

        test("should change the url when the label change, changing to the suitable protocol (2)", async () => {
            await testEditor({
                contentBefore: '<p>a<a href="mailto:hello@moto.com">hello@[]moto.com</a></p>',
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                },
                contentAfter: '<p>a<a href="https://hellomoto.com">hello[]moto.com</a></p>',
            });
        });

        test("should change the url in one step", async () => {
            await testEditor({
                contentBefore: '<p>a<a href="https://google.co">google.co[]</a>b</p>',
                stepFunction: async (editor) => {
                    await insertText(editor, "m");
                    await undo(editor);
                },
                contentAfter: '<p>a<a href="https://google.co">google.co[]</a>b</p>',
            });
        });

        test("should not change the url when the label change (1)", async () => {
            await testEditor({
                contentBefore: '<p>a<a href="https://google.com">google.com[]</a>b</p>',
                stepFunction: async (editor) => {
                    await insertText(editor, "u");
                },
                contentAfter: '<p>a<a href="https://google.com">google.comu[]</a>b</p>',
            });
        });

        test("should not change the url when the label change (2)", async () => {
            await testEditor({
                contentBefore: '<p>a<a href="https://google.com">google.com[]</a>b</p>',
                stepFunction: async (editor) => {
                    await animationFrame();
                    await insertLineBreak(editor);
                    await insertText(editor, "odoo.com");
                },
                contentAfter: '<p>a<a href="https://google.com">google.com</a><br>odoo.com[]b</p>',
            });
        });
    });

    describe("range not collapsed", () => {
        test("should change the url when the label change (1)", async () => {
            await testEditor({
                contentBefore: '<p>a<a href="https://google.com">google.[com]</a>b</p>',
                stepFunction: async (editor) => {
                    await insertText(editor, "be");
                },
                contentAfter: '<p>a<a href="https://google.be">google.be[]</a>b</p>',
            });
        });

        test("should change the url when the label change (2)", async () => {
            await testEditor({
                contentBefore: '<p>a<a href="https://gogle.com">[yahoo].com</a>b</p>',
                stepFunction: async (editor) => {
                    await insertText(editor, "google");
                },
                contentAfter: '<p>a<a href="https://gogle.com">google[].com</a>b</p>',
            });
        });

        test("should change the url when the label change (3)", async () => {
            await testEditor({
                contentBefore: '<p>a<a href="https://else.com">go[gle.c]om</a>b</p>',
                stepFunction: async (editor) => {
                    await insertText(editor, ".c");
                },
                contentAfter: '<p>a<a href="https://else.com">go.c[]om</a>b</p>',
            });
        });

        test("should not change the url when the label change (1)", async () => {
            await testEditor({
                contentBefore: '<p>a<a href="https://google.com">googl[e.com]</a>b</p>',
                stepFunction: async (editor) => {
                    await insertText(editor, "e");
                },
                contentAfter: '<p>a<a href="https://google.com">google[]</a>b</p>',
            });
        });

        test("should not change the url when the label change (2)", async () => {
            await testEditor({
                contentBefore: '<p>a<a href="https://google.com">google.[com]</a>b</p>',
                stepFunction: async (editor) => {
                    await insertText(editor, "vvv");
                },
                contentAfter: '<p>a<a href="https://google.com">google.vvv[]</a>b</p>',
            });
        });
    });
});

describe("correct incorrect URLs when editing", () => {
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

describe("edit links from templates", () => {
    test("should not remove a link with t-attf-href", async () => {
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
    test("should not remove a link with t-att-href", async () => {
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

describe.tags("desktop");
describe("format links", () => {
    test("click on link, the link popover should load the current format correctly", async () => {
        await setupEditor(
            '<p><a href="http://test.com/" class="btn btn-fill-primary">link2[]</a></p>'
        );
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await animationFrame();
        expect(".o_we_label_link").toHaveValue("link2");
        expect(".o_we_href_input_link").toHaveValue("http://test.com/");
        expect(queryOne("button[name='link_type']").textContent).toBe("Button Primary");
    });
    test("after changing the link format, the link should be updated", async () => {
        const { el } = await setupEditor(
            '<p><a href="http://test.com/" class="btn btn-fill-secondary">link2[]</a></p>'
        );
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await animationFrame();

        expect(queryOne("button[name='link_type']").textContent).toBe("Button Secondary");

        await click("button[name='link_type']");
        await animationFrame();
        await click(".o-we-link-type-dropdown .dropdown-item:contains('Button Primary')");
        await animationFrame();
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            `<p><a href="http://test.com/" class="btn btn-fill-primary">link2</a></p>`
        );
    });
    test("after changing the link format, the link should be updated (2)", async () => {
        const { el } = await setupEditor(
            '<p><a href="http://test.com/" class="btn btn-secondary">link2[]</a></p>'
        );
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await animationFrame();

        expect(queryOne("button[name='link_type']").textContent).toBe("Button Secondary");

        await click("button[name='link_type']");
        await animationFrame();
        await click(".o-we-link-type-dropdown .dropdown-item:contains('Button Primary')");
        await animationFrame();
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

        expect(queryOne("button[name='link_type']").textContent).toBe("Button Secondary");

        await click("button[name='link_type']");
        await animationFrame();
        await click(".o-we-link-type-dropdown .dropdown-item:contains('Button Primary')");
        await animationFrame();
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            `<p><a href="http://test.com/" class="random-css-class text-muted btn btn-outline-primary">link2</a></p>`
        );
    });
    test("after applying the link format, the link's format should be updated", async () => {
        const { el } = await setupEditor('<p><a href="http://test.com/">link2[]</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await animationFrame();
        expect(queryOne("button[name='link_type']").textContent).toBe("Link");

        await click("button[name='link_type']");
        await animationFrame();
        await click(".o-we-link-type-dropdown .dropdown-item:contains('Button Secondary')");
        await animationFrame();

        await click(".o_we_apply_link");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            '<p><a href="http://test.com/" class="btn btn-secondary">link2[]</a></p>'
        );
    });
    test("clicking the discard button should revert the link format", async () => {
        const { el } = await setupEditor('<p><a href="http://test.com/">link1[]</a></p>');
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await contains(".o-we-linkpopover input.o_we_label_link").edit("link2");
        await click("button[name='link_type']");
        await animationFrame();
        await click(".o-we-link-type-dropdown .dropdown-item:contains('Button Secondary')");
        await animationFrame();
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

        await click("button[name='link_type']");
        await animationFrame();
        await click(".o-we-link-type-dropdown .dropdown-item:contains('Button Secondary')");
        await animationFrame();
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
    test("link_type dropdown should show a preview of preset with primary and secondary color.", async () => {
        const { el } = await setupEditor(`<p><a href="http://test.com/">link1[]</a></p>`);
        await waitFor(".o-we-linkpopover");
        await click(".o_we_edit_link");
        await animationFrame();
        await click("button[name='link_type']");
        await animationFrame();
        const dropdownItems = queryAll(".o-we-link-type-dropdown .dropdown-item span");
        expect(dropdownItems[0]).toHaveStyle({ color: "rgb(0, 143, 140)" });
        expect(dropdownItems[1]).toHaveClass("btn btn-primary btn-sm");
        expect(dropdownItems[2]).toHaveClass("btn btn-secondary btn-sm");
        await click(dropdownItems[1]);
        await animationFrame();
        expect("button[name='link_type'] span").toHaveClass("btn btn-primary btn-sm");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            `<p><a href="http://test.com/" class="btn btn-primary">link1</a></p>`
        );
    });
});
