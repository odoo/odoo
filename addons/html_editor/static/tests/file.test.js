import { MAIN_EMBEDDINGS } from "@html_editor/others/embedded_components/embedding_sets";
import {
    EMBEDDED_COMPONENT_PLUGINS,
    MAIN_PLUGINS,
    NO_EMBEDDED_COMPONENTS_FALLBACK_PLUGINS,
} from "@html_editor/plugin_sets";
import { isZwnbsp } from "@html_editor/utils/dom_info";
import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, press, queryOne, waitFor } from "@odoo/hoot-dom";
import { onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupEditor } from "./_helpers/editor";
import { getContent, setSelection } from "./_helpers/selection";
import { insertText, undo } from "./_helpers/user_actions";
import { execCommand } from "./_helpers/userCommands";
import { dispatchCleanForSave } from "./_helpers/dispatch";

const configWithEmbeddedFile = {
    Plugins: [...MAIN_PLUGINS, ...EMBEDDED_COMPONENT_PLUGINS],
    resources: { embedded_components: MAIN_EMBEDDINGS },
};

const configWithoutEmbeddedFile = {
    Plugins: [...MAIN_PLUGINS, ...NO_EMBEDDED_COMPONENTS_FALLBACK_PLUGINS],
};

const patchUpload = (editor, nbrFiles = 1, lag = 0) => {
    const mockedUploadPromise = new Promise((resolve) => {
        patchWithCleanup(editor.services.uploadLocalFiles, {
            async upload() {
                if (lag) {
                    await new Promise((r) => setTimeout(r, lag));
                }
                const files = [];
                for (let i = 0; i < nbrFiles; i++) {
                    files.push({ id: i + 1, name: "file.txt", mimetype: "text/plain" });
                }
                resolve();
                return files;
            },
        });
    });
    return mockedUploadPromise;
};
const fileBoxRegex =
    /<span class="o_file_box (?:(?!mimetype).)+mimetype="([^"]+)"(?:(?!mimetype).)+<\/span>/g;
const getReplacedContent = (el) => getContent(el).replaceAll(fileBoxRegex, "<fileBox:$1>");

describe("file command", () => {
    test("/file uploads a file via the system's selector, skipping the media dialog", async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", {
            config: configWithoutEmbeddedFile,
        });
        const mockedUpload = patchUpload(editor);
        // Open powerbox.
        await insertText(editor, "/file");
        await animationFrame();
        // Select first command ("Upload a file")
        await press("Enter");
        await animationFrame();
        // Check that there's no media dialog.
        expect(".o_select_media_dialog").toHaveCount(0);
        await mockedUpload;
        // Check that file card (embedded component) was inserted in the editable.
        expect(".odoo-editor-editable .o_file_box").toHaveCount(1);
    });

    test("file card should have inline display, BS alert-info style and no download button", async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", {
            config: configWithoutEmbeddedFile,
        });
        patchUpload(editor);
        execCommand(editor, "uploadFile");
        // wait for the embedded component to be mounted
        await waitFor('.o_file_box .o_file_name_container:contains("file.txt")');
        // Check that file card has inline display, with alert style.
        const fileCard = queryOne(".o_file_box");
        expect(fileCard).toHaveStyle({ display: "inline-block" });
        expect(fileCard.firstElementChild).toHaveClass(["alert", "alert-info"]);
        // No download button in file card.
        expect(".o_file_box .fa-download").toHaveCount(0);
    });
    test("file uploaded with network lag should insert a file card at the initial selection location", async () => {
        const { editor, el } = await setupEditor("<p>a[]b<b>c</b></p>", {
            config: configWithoutEmbeddedFile,
        });
        patchUpload(editor, 1, 50);
        execCommand(editor, "uploadFile");
        // should have temporay card
        expect(getReplacedContent(el)).toBe(`<p>a\ufeff<fileBox:uploading>\ufeff[]b<b>c</b></p>`);
        // move selection
        const bChild = el.querySelector("p>b");
        setSelection({ anchorNode: bChild, anchorOffset: 0, focusNode: bChild, focusOffset: 0 });
        expect(getReplacedContent(el)).toBe(`<p>a\ufeff<fileBox:uploading>\ufeffb<b>[]c</b></p>`);
        // wait for the file to be uploaded
        await new Promise((r) => setTimeout(r, 100));
        // temporay card should be replaced with real file card
        expect(getReplacedContent(el)).toBe(`<p>a\ufeff<fileBox:text/plain>\ufeffb<b>[]c</b></p>`);
    });
    test("multiple file uploaded with network lag should insert files cards at the initial selection location", async () => {
        const { editor, el } = await setupEditor("<p>a[]b<b>c</b></p>", {
            config: configWithoutEmbeddedFile,
        });
        patchUpload(editor, 2, 50);
        execCommand(editor, "uploadFile");
        // should have temporay card
        expect(getReplacedContent(el)).toBe(`<p>a\ufeff<fileBox:uploading>\ufeff[]b<b>c</b></p>`);
        // move selection
        const bChild = el.querySelector("p>b");
        setSelection({ anchorNode: bChild, anchorOffset: 0, focusNode: bChild, focusOffset: 0 });
        expect(getReplacedContent(el)).toBe(`<p>a\ufeff<fileBox:uploading>\ufeffb<b>[]c</b></p>`);
        // wait for the file to be uploaded
        await new Promise((r) => setTimeout(r, 100));
        // temporay card should be replaced with real file card
        expect(getReplacedContent(el)).toBe(
            `<p>a\ufeff<fileBox:text/plain>\ufeff<fileBox:text/plain>\ufeffb<b>[]c</b></p>`
        );
    });
    test("uploaded with lag handle undo correctly", async () => {
        const { editor, el } = await setupEditor("<p>a[]b<b>c</b></p>", {
            config: configWithoutEmbeddedFile,
        });
        patchUpload(editor, 1, 50);
        execCommand(editor, "uploadFile");
        // should have temporay card
        expect(getReplacedContent(el)).toBe(`<p>a\ufeff<fileBox:uploading>\ufeff[]b<b>c</b></p>`);
        // move selection
        const bChild = el.querySelector("p>b");
        setSelection({ anchorNode: bChild, anchorOffset: 0, focusNode: bChild, focusOffset: 0 });
        expect(getReplacedContent(el)).toBe(`<p>a\ufeff<fileBox:uploading>\ufeffb<b>[]c</b></p>`);
        await insertText(editor, "x");
        expect(getReplacedContent(el)).toBe(`<p>a\ufeff<fileBox:uploading>\ufeffb<b>x[]c</b></p>`);
        // wait for the file to be uploaded
        await new Promise((r) => setTimeout(r, 100));
        // temporary card should be replaced with real file card
        expect(getReplacedContent(el)).toBe(`<p>a\ufeff<fileBox:text/plain>\ufeffb<b>x[]c</b></p>`);
        undo(editor);
        expect(getReplacedContent(el)).toBe(`<p>ab<b>x[]c</b></p>`);
        undo(editor);
        expect(getReplacedContent(el)).toBe(`<p>ab<b>[]c</b></p>`);
    });
    test("temporary file card should not be saved", async () => {
        const { editor, el } = await setupEditor("<p>a[]b<b>c</b></p>", {
            config: configWithoutEmbeddedFile,
        });
        patchUpload(editor, 1, 50);
        execCommand(editor, "uploadFile");
        // should have temporay card
        expect(getReplacedContent(el)).toBe(`<p>a\ufeff<fileBox:uploading>\ufeff[]b<b>c</b></p>`);
        // move selection
        const bChild = el.querySelector("p>b");
        setSelection({ anchorNode: bChild, anchorOffset: 0, focusNode: bChild, focusOffset: 0 });
        expect(getReplacedContent(el)).toBe(`<p>a\ufeff<fileBox:uploading>\ufeffb<b>[]c</b></p>`);
        await insertText(editor, "x");
        expect(getReplacedContent(el)).toBe(`<p>a\ufeff<fileBox:uploading>\ufeffb<b>x[]c</b></p>`);
        // wait for the file to be uploaded
        dispatchCleanForSave(editor, { root: el });
        // wait to ensure the cleanForSave handlers did not create issue when upload finish
        await new Promise((r) => setTimeout(r, 100));
        expect(getReplacedContent(el)).toBe(`<p>ab<b>x[]c</b></p>`);
    });
});

describe("document tab in media dialog", () => {
    onRpc("ir.attachment", "search_read", () => [
        {
            id: 1,
            name: "file.txt",
            mimetype: "text/plain",
            public: true,
            image_src: "",
        },
    ]);

    describe("without File nor EmbeddedFile plugin", () => {
        test("Document tab is not available by default", async () => {
            const { editor } = await setupEditor("<p>[]<br></p>", {
                config: { Plugins: MAIN_PLUGINS },
            });
            execCommand(editor, "insertMedia");
            await animationFrame();
            expect(".nav-link:contains('Documents')").toHaveCount(0);
        });
    });

    describe("with EmbeddedFile plugin", () => {
        test("file upload via media dialog inserts a file card in the editable", async () => {
            const { editor } = await setupEditor("<p>[]<br></p>", {
                config: configWithEmbeddedFile,
            });
            execCommand(editor, "insertMedia");
            await animationFrame();
            await click(".nav-link:contains('Documents')");
            await animationFrame();
            await click(".o_we_attachment_highlight .o_button_area");
            // wait for the embedded component to be mounted
            await waitFor('[data-embedded="file"] .o_file_name:contains("file.txt")');
            expect('[data-embedded="file"]').toHaveCount(1);
        });
    });

    describe("with File plugin (no embedded component)", () => {
        test("file upload via media dialog inserts a link in the editable", async () => {
            const { editor } = await setupEditor("<p>[]<br></p>", {
                config: configWithoutEmbeddedFile,
            });
            execCommand(editor, "insertMedia");
            await animationFrame();
            await click(".nav-link:contains('Documents')");
            await animationFrame();
            await click(".o_we_attachment_highlight .o_button_area");
            expect(".odoo-editor-editable .o_file_box a:contains('file.txt')").toHaveCount(1);
        });
    });
});

describe("powerbutton", () => {
    test("file powerbutton uploads a file directly via the system's selector", async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", {
            config: configWithoutEmbeddedFile,
        });
        const mockedUpload = patchUpload(editor);
        // Click on the upload powerbutton.
        await click(".power_button.fa-upload");
        await animationFrame();
        // Check that there's no media dialog.
        expect(".o_select_media_dialog").toHaveCount(0);
        await mockedUpload;
        // Check that file card (embedded component) was inserted in the editable.
        expect(".odoo-editor-editable .o_file_box").toHaveCount(1);
    });

    test("file powerbutton uploads a file directly via the system's selector (embedded component)", async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", { config: configWithEmbeddedFile });
        const mockedUpload = patchUpload(editor);
        // Click on the upload powerbutton.
        await click(".power_button.fa-upload");
        await animationFrame();
        // Check that there's no media dialog.
        expect(".o_select_media_dialog").toHaveCount(0);
        await mockedUpload;
        // Check that file card (embedded component) was inserted in the editable.
        expect('.odoo-editor-editable [data-embedded="file"]').toHaveCount(1);
    });
});

describe("zero width no-break space", () => {
    test("file card should be padded with zero-width no-break spaces", async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", {
            config: configWithoutEmbeddedFile,
        });
        patchUpload(editor);
        execCommand(editor, "uploadFile");
        // wait for the the file to be uploaded and the card rendered
        await waitFor('.o_file_box a:contains("file.txt")');
        // Check that file card is padded with ZWNBSP on both sides.
        const fileCard = queryOne(".o_file_box");
        expect(isZwnbsp(fileCard.previousSibling)).toBe(true);
        expect(isZwnbsp(fileCard.nextSibling)).toBe(true);
    });

    test("should not add two contiguous ZWNBSP between two file cards", async () => {
        const { editor, el } = await setupEditor("<p>[]<br></p>", {
            config: { ...configWithEmbeddedFile, resources: { embedded_components: [] } }, // disable embedded component rendering
        });
        let mockUpload = patchUpload(editor);
        execCommand(editor, "uploadFile");
        await mockUpload;
        // patch again to get new Promise
        mockUpload = patchUpload(editor);
        execCommand(editor, "uploadFile");
        await mockUpload;
        let content = getContent(el);
        // replace embedded component root with a <FILE/> placeholder for readability
        content = content.replace(/<span data-embedded="file".*?<\/span>/g, "<FILE/>");
        expect(content).toBe("<p>\ufeff<FILE/>\ufeff<FILE/>\ufeff[]</p>");
    });

    test("should not add two contiguous ZWNBSP between two file cards (2)", async () => {
        const { el } = await setupEditor(
            '<p>abc<span data-embedded="file" class="o_file_box"></span>x[]<span data-embedded="file" class="o_file_box"></span></p>',
            { config: { ...configWithEmbeddedFile, resources: { embedded_components: [] } } } // disable embedded component rendering
        );
        expect(getContent(el)).toBe(
            '<p>abc\ufeff<span data-embedded="file" class="o_file_box"></span>\ufeffx[]\ufeff<span data-embedded="file" class="o_file_box"></span>\ufeff</p>'
        );
        press("Backspace");
        expect(getContent(el)).toBe(
            '<p>abc\ufeff<span data-embedded="file" class="o_file_box"></span>\ufeff[]<span data-embedded="file" class="o_file_box"></span>\ufeff</p>'
        );
    });
});
