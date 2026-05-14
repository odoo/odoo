import { expect, test, waitFor } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

import { FileModel } from "@web/core/file_viewer/file_model";
import { FileViewer } from "@web/core/file_viewer/file_viewer";

test("can delete an attachment from the file viewer", async () => {
    const attachment = Object.assign(new FileModel(), {
        id: 1,
        name: "test_image.png",
        mimetype: "image/png",
    });
    await mountWithCleanup(FileViewer, {
        props: {
            files: [attachment],
            startIndex: 0,
            canUnlink: () => true,
            onUnlink: (file) => {
                expect.step(`delete_file ${file.name}`);
                return true;
            },
        },
    });
    await waitFor(".o-FileViewer");
    await click(".o-FileViewer-headerButton[title='Remove']");
    expect.verifySteps(["delete_file test_image.png"]);
});
