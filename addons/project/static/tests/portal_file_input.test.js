import { expect, test } from "@odoo/hoot";
import { setInputFiles } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    contains,
    patchWithCleanup,
    mountWithCleanup,
    mockService,
} from "@web/../tests/web_test_helpers";
import { session } from "@web/session";

import { PortalFileInput } from "@project/project_sharing/components/portal_file_input/portal_file_input";

mockService("notification", () => ({
    add(message) {
        expect.step("notification");
        expect(message).toBe("The selected file (4B) is over the maximum allowed file size (2B).");
    },
}));
mockService("http", () => ({
    post(route) {
        expect.step(route);
        return "[]";
    },
}));

test("check that uploading a file that is too heavy in portal sends a notification", async (assert) => {
    patchWithCleanup(odoo, { csrf_token: "dummy" });
    patchWithCleanup(session, { max_file_upload_size: 2 });
    await mountWithCleanup(PortalFileInput, {
        onUpload(files) {
            assert.deepEqual(files, [null]);
        },
    });

    const file = new File(["test"], "fake_file.txt", { type: "text/plain" });
    await contains(".o_file_input input", { visible: false }).click();
    setInputFiles([file]);
    await animationFrame();
    expect(["notification"]).toVerifySteps({
        message: "Only the notification should be triggered and the file shouldn't be uploaded",
    });
});
