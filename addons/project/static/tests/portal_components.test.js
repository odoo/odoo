import { describe, expect, test } from "@odoo/hoot";
import { session } from "@web/session";
import { mountWithCleanup, patchWithCleanup, mockService, contains } from "@web/../tests/web_test_helpers";
import { PortalFileInput } from "@project/project_sharing/components/portal_file_input/portal_file_input";
import { setInputFiles } from "@odoo/hoot-dom";

describe.current.tags("desktop");

async function createFileInput({ mockPost, mockAdd, props }) {
    mockService("notification", {
        add: mockAdd || (() => {}),
    });
    mockService("http", {
        post: mockPost || (() => {}),
    });
    await mountWithCleanup(PortalFileInput, { props });
}

test("uploading a file that is too heavy in portal will send a notification", async () => {
    patchWithCleanup(session, { max_file_upload_size: 2 });
    await createFileInput({
        props: {
            onUpload(files) {
                expect(files).toEqual([null]);
            },
        },
        mockAdd: (message) => {
            expect.step("notification");
            expect(message).toBe("The selected file (4B) is over the maximum allowed file size (2B).");
        },
    });

    const file = new File(["test"], "fake_file.txt", { type: "text/plain" });
    await contains(".o_file_input input", { visible: false }).click();
    setInputFiles([file]);
    expect(["notification"]).toVerifySteps();
});
