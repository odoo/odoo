import { CORE_PLUGINS } from "@html_editor/plugin_sets";
import { describe, expect, test } from "@odoo/hoot";
import { click, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains } from "@web/../tests/web_test_helpers";
import { setupEditor, setupWysiwyg } from "./_helpers/editor";
import {
    getContent,
    moveSelectionOutsideEditor,
    setContent,
    setSelection,
} from "./_helpers/selection";

describe("Wysiwyg Component", () => {
    test("Wysiwyg component can be instantiated", async () => {
        const { el } = await setupWysiwyg();
        expect(".o-wysiwyg").toHaveCount(1);
        expect(".odoo-editor-editable").toHaveCount(1);
        expect(".o-we-toolbar").toHaveCount(0);

        // set the selection to a range, and check that the toolbar
        // is opened
        expect(getContent(el)).toBe("");
        setContent(el, "hello [hoot]");
        await animationFrame();
        expect(".o-we-toolbar").toHaveCount(1);
    });

    test("Wysiwyg component can be instantiated with initial content", async () => {
        const { el } = await setupWysiwyg({
            config: { content: "<p>hello rodolpho</p>" },
        });
        expect(el.innerHTML).toBe(`<p>hello rodolpho</p>`);
    });

    test("Wysiwyg component can be instantiated with a permanent toolbar", async () => {
        expect(".o-we-toolbar").toHaveCount(0);
        await setupWysiwyg({ toolbar: true });
        expect(".o-wysiwyg").toHaveCount(1);
        expect(".odoo-editor-editable").toHaveCount(1);
        expect(".o-we-toolbar").toHaveCount(1);
    });

    test("Wysiwyg component can't display a permanent toolbar if toolbar plugin is missing", async () => {
        expect(".o-we-toolbar").toHaveCount(0);
        await setupWysiwyg({ toolbar: true, config: { Plugins: CORE_PLUGINS } });
        expect(".o-wysiwyg").toHaveCount(1);
        expect(".odoo-editor-editable").toHaveCount(1);
        expect(".o-we-toolbar").toHaveCount(0);
    });

    test("wysiwyg with toolbar: buttons react to selection change", async () => {
        const { el } = await setupWysiwyg({
            toolbar: true,
            config: { content: "<p>test some text</p>" },
        });
        expect(el.innerHTML).toBe(`<p>test some text</p>`);

        setContent(el, "<p>test [some] text</p>");
        await waitFor(".o-we-toolbar .btn[name='bold']:not(.active)");

        await contains(".btn[name='bold']").click();
        expect(getContent(el)).toBe("<p>test <strong>[some]</strong> text</p>");
        await waitFor(".o-we-toolbar .btn[name='bold'].active");

        setContent(el, "<p>test <strong>some</strong> text[]</p>");
        await waitFor(".o-we-toolbar .btn[name='bold']:not(.active)");

        setContent(el, "<p>test <strong>some[]</strong> text</p>");
        await waitFor(".o-we-toolbar .btn[name='bold'].active");
    });

    test("wysiwyg with toolbar: properly behave when selection leaves editable", async () => {
        const { el } = await setupEditor("<p>test <strong>[some]</strong> text</p>", {
            props: { toolbar: true },
        });

        await animationFrame();
        expect(".o-we-toolbar .btn[name='bold']").toHaveClass("active");

        await click(document.body);
        moveSelectionOutsideEditor();
        await animationFrame();
        expect(getContent(el)).toBe("<p>test <strong>some</strong> text</p>");
        expect(".o-we-toolbar .btn[name='bold']").toHaveClass("active");
    });

    test("wysiwyg with toolbar: remember last active selection", async () => {
        const { el } = await setupEditor("<p>test [some] text</p>", {
            props: { toolbar: true },
        });
        await waitFor(".o-we-toolbar .btn[name='bold']:not(.active)");

        await click(document.body);
        moveSelectionOutsideEditor();
        await animationFrame();
        expect(getContent(el)).toBe("<p>test some text</p>");
        await waitFor(".o-we-toolbar .btn[name='bold']:not(.active)");
        await click(".o-we-toolbar .btn[name='bold']");
        expect(getContent(el)).toBe("<p>test <strong>[some]</strong> text</p>");
        await waitFor(".o-we-toolbar .btn[name='bold'].active");
    });

    test("Wysiwyg in iframe with a contentClass that need to be trim", async () => {
        await setupWysiwyg({
            iframe: true,
            contentClass: "test ",
        });
        expect(":iframe .test.odoo-editor-editable").toHaveCount(1);
    });

    test.tags("desktop")("wysiwyg in iframe: toolbar should be well positioned", async () => {
        const CLOSE_ENOUGH = 10;
        const { el } = await setupWysiwyg({
            iframe: true,
            config: { content: "<p>editable text inside the iframe</p>".repeat(30) },
        });

        // Add some content before the iframe to make sure it's top does not
        // match the top window's top (i.e. create a vertical offset).
        const iframe = document.querySelector("iframe");
        for (let i = 0; i < 10; i++) {
            const p = document.createElement("p");
            p.textContent = "content outside the iframe";
            iframe.before(p);
        }
        const iframeOffset = iframe.getBoundingClientRect().top;

        // Select a paragraph's content to display the toolbar.
        const p = el.childNodes[5];
        setSelection({ anchorNode: p, anchorOffset: 0, focusNode: p, focusOffset: 1 });
        const toolbar = await waitFor(".o-we-toolbar");

        // Check that toolbar is on top of and close to the selected paragraph.
        const pTop = p.getBoundingClientRect().top + iframeOffset;
        const toolbarBottom = toolbar.getBoundingClientRect().bottom;
        expect(pTop - toolbarBottom).toBeWithin(0, CLOSE_ENOUGH);
    });
});
