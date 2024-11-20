import { describe, expect, test } from "@odoo/hoot";
import { setupEditor } from "./_helpers/editor";
import { EMBEDDED_COMPONENT_PLUGINS, MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { insertText } from "./_helpers/user_actions";
import { animationFrame, press } from "@odoo/hoot-dom";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { MAIN_EMBEDDINGS } from "@html_editor/others/embedded_components/embedding_sets";

const config = {
    Plugins: [...MAIN_PLUGINS, ...EMBEDDED_COMPONENT_PLUGINS],
    resources: { embedded_components: MAIN_EMBEDDINGS },
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
        const { editor } = await setupEditor("<p>[]<br></p>", { config });
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
        expect('.odoo-editor-editable [data-embedded="file"]').toHaveCount(1);
    });
});
