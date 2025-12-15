import { MAIN_EMBEDDINGS } from "@html_editor/others/embedded_components/embedding_sets";
import {
    EMBEDDED_COMPONENT_PLUGINS,
    MAIN_PLUGINS,
    NO_EMBEDDED_COMPONENTS_FALLBACK_PLUGINS,
} from "@html_editor/plugin_sets";
import { isZwnbsp } from "@html_editor/utils/dom_info";
import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, press, queryAll, queryOne, waitFor } from "@odoo/hoot-dom";
import { onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupEditor } from "./_helpers/editor";
import { getContent } from "./_helpers/selection";
import { insertText } from "./_helpers/user_actions";
import { execCommand } from "./_helpers/userCommands";
import { expandToolbar } from "./_helpers/toolbar";
import { nodeSize } from "@html_editor/utils/position";

const configWithEmbeddedFile = {
    Plugins: [...MAIN_PLUGINS, ...EMBEDDED_COMPONENT_PLUGINS],
    resources: { embedded_components: MAIN_EMBEDDINGS },
};

const configWithoutEmbeddedFile = {
    Plugins: [...MAIN_PLUGINS, ...NO_EMBEDDED_COMPONENTS_FALLBACK_PLUGINS],
};

const patchUpload = (editor) => {
    const mockedUploadPromise = new Promise((resolve) => {
        patchWithCleanup(editor.services.uploadLocalFiles, {
            async upload() {
                resolve();
                return [{ id: 1, name: "file.txt" }];
            },
        });
    });
    return mockedUploadPromise;
};

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

    describe("static file box interactions", () => {
        test.tags("desktop");
        test("should toggle file name editability independently on click", async () => {
            const { el, editor } = await setupEditor("<p>[]<br></p>", {
                config: configWithoutEmbeddedFile,
            });
            patchUpload(editor);

            // Upload two files.
            execCommand(editor, "uploadFile");
            execCommand(editor, "uploadFile");

            // Wait until both file names are rendered.
            await waitFor('.o_file_box .o_file_name_container:contains("file.txt")');

            const [fileNameEl1, fileNameEl2] = queryAll(
                ".o_file_box .o_file_name_container .o_link_readonly"
            );

            // File names are read-only by default.
            expect(fileNameEl1).toHaveAttribute("contenteditable", "false");
            expect(fileNameEl2).toHaveAttribute("contenteditable", "false");

            // Clicking the first file name enables editing only for that file.
            await click(fileNameEl1);
            await animationFrame();

            expect(fileNameEl1).toHaveAttribute("contenteditable", "true");
            expect(fileNameEl2).toHaveAttribute("contenteditable", "false");

            editor.shared.selection.setSelection({
                anchorNode: fileNameEl1,
                anchorOffset: 0,
                focusNode: fileNameEl1,
                focusOffset: nodeSize(fileNameEl1),
            });
            await animationFrame();
            expect(getContent(fileNameEl1)).toBe("[file.txt]");
            // File name editing should not open the editor toolbar.
            expect(".o-we-toolbar").toHaveCount(0);

            // Clicking the second file name transfers editability to it.
            await click(fileNameEl2);
            await animationFrame();

            expect(fileNameEl1).toHaveAttribute("contenteditable", "false");
            expect(fileNameEl2).toHaveAttribute("contenteditable", "true");

            editor.shared.selection.setSelection({
                anchorNode: fileNameEl2,
                anchorOffset: 0,
                focusNode: fileNameEl2,
                focusOffset: nodeSize(fileNameEl2),
            });
            await animationFrame();
            expect(getContent(fileNameEl2)).toBe("[file.txt]");
            // File name editing should not open the editor toolbar.
            expect(".o-we-toolbar").toHaveCount(0);

            // Clicking outside exits file name editing for all files.
            const paragraph = el.firstElementChild;
            await click(paragraph);

            editor.shared.selection.setCursorStart(paragraph);
            await animationFrame(); // Wait for selection change.

            expect(fileNameEl1).toHaveAttribute("contenteditable", "false");
            expect(fileNameEl2).toHaveAttribute("contenteditable", "false");
        });

        test.tags("desktop");
        test("ArrowUp and ArrowDown move the caret to the start and end of a file name", async () => {
            const { editor } = await setupEditor("<p>[]<br></p>", {
                config: configWithoutEmbeddedFile,
            });
            patchUpload(editor);

            // Upload a file and wait until the file name is rendered.
            execCommand(editor, "uploadFile");
            await waitFor('.o_file_box .o_file_name_container:contains("file.txt")');

            const fileNameEl = queryOne(".o_file_box .o_file_name_container .o_link_readonly");

            // File name is read-only by default.
            expect(fileNameEl).toHaveAttribute("contenteditable", "false");

            // Enable editing on the file name.
            await click(fileNameEl);
            await animationFrame();

            expect(fileNameEl).toHaveAttribute("contenteditable", "true");

            // Place cursor in the start of the file name.
            editor.shared.selection.setCursorStart(fileNameEl);
            await animationFrame();
            expect(getContent(fileNameEl)).toBe("[]file.txt");

            // ArrowDown moves the caret to the end of the file name.
            await press("ArrowDown");
            expect(getContent(fileNameEl)).toBe("file.txt[]");

            // ArrowUp moves the caret to the start of the file name.
            await press("ArrowUp");
            expect(getContent(fileNameEl)).toBe("[]file.txt");
        });

        test.tags("desktop");
        test("ArrowLeft at start and ArrowRight at end do nothing in a file name", async () => {
            const { editor } = await setupEditor("<p>[]<br></p>", {
                config: configWithoutEmbeddedFile,
            });
            patchUpload(editor);

            // Upload a file and wait until the file name is rendered.
            execCommand(editor, "uploadFile");
            await waitFor('.o_file_box .o_file_name_container:contains("file.txt")');

            const fileNameEl = queryOne(".o_file_box .o_file_name_container .o_link_readonly");

            // Enable editing on the file name.
            await click(fileNameEl);
            await animationFrame();

            // Place cursor at the start of the file name.
            editor.shared.selection.setCursorStart(fileNameEl);
            await animationFrame();
            expect(getContent(fileNameEl)).toBe("[]file.txt");

            // ArrowLeft at start should do nothing.
            await press("ArrowLeft");
            expect(getContent(fileNameEl)).toBe("[]file.txt");

            // Place cursor at the end of the file name.
            editor.shared.selection.setCursorEnd(fileNameEl);
            await animationFrame();
            expect(getContent(fileNameEl)).toBe("file.txt[]");

            // ArrowRight at end should do nothing.
            await press("ArrowRight");
            expect(getContent(fileNameEl)).toBe("file.txt[]");
        });

        test.tags("desktop");
        test("Enter and Shift+Enter do nothing in a file name", async () => {
            const { editor } = await setupEditor("<p>[]<br></p>", {
                config: configWithoutEmbeddedFile,
            });
            patchUpload(editor);

            // Upload a file and wait until the file name is rendered.
            execCommand(editor, "uploadFile");
            await waitFor('.o_file_box .o_file_name_container:contains("file.txt")');

            const fileNameEl = queryOne(".o_file_box .o_file_name_container .o_link_readonly");

            // Enable editing on the file name.
            await click(fileNameEl);
            await animationFrame();

            // Place cursor at the start of the file name.
            editor.shared.selection.setCursorStart(fileNameEl);
            await animationFrame();
            expect(getContent(fileNameEl)).toBe("[]file.txt");

            // Enter should do nothing.
            await press("Enter");
            expect(getContent(fileNameEl)).toBe("[]file.txt");

            // Place cursor at the end of the file name.
            editor.shared.selection.setCursorEnd(fileNameEl);
            await animationFrame();
            expect(getContent(fileNameEl)).toBe("file.txt[]");

            // Shift+Enter should do nothing.
            await press(["shift", "Enter"]);
            expect(getContent(fileNameEl)).toBe("file.txt[]");
        });
    });
});

test("Should not apply color to file box", async () => {
    const { editor } = await setupEditor("<p>a[]b</p>", {
        config: configWithEmbeddedFile,
    });
    const mockedUpload = patchUpload(editor);
    await insertText(editor, "/file");
    await animationFrame();
    await press("Enter");
    await animationFrame();
    expect(".o_select_media_dialog").toHaveCount(0);
    await mockedUpload;
    await press(["Ctrl", "a"]);
    await animationFrame();
    await expandToolbar();
    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    await click('.o_colorpicker_section [data-color="o-color-1"]');
    await animationFrame();
    const fileBox = queryOne(".o_file_box");
    expect(fileBox).not.toHaveClass("text-o-color-1");
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
            config: { ...configWithEmbeddedFile, resources: {} }, // disable embedded component rendering
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
            { config: { ...configWithEmbeddedFile, resources: {} } } // disable embedded component rendering
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
