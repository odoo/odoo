import { CORE_PLUGINS } from "@html_editor/plugin_sets";
import { describe, expect, test } from "@odoo/hoot";
import { click, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains } from "@web/../tests/web_test_helpers";
import { setupEditor, setupWysiwyg } from "./_helpers/editor";
import { getContent, moveSelectionOutsideEditor, setContent } from "./_helpers/selection";

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
            config: { content: "<p>test some text</p>", disableFloatingToolbar: true },
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

        click(document.body);
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

        click(document.body);
        moveSelectionOutsideEditor();
        await animationFrame();
        expect(getContent(el)).toBe("<p>test some text</p>");
        await waitFor(".o-we-toolbar .btn[name='bold']:not(.active)");
        click(".o-we-toolbar .btn[name='bold']");
        expect(getContent(el)).toBe("<p>test <strong>[some]</strong> text</p>");
        await waitFor(".o-we-toolbar .btn[name='bold'].active");
    });
});
