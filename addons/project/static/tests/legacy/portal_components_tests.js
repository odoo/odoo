/** @odoo-module **/

import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import {
    editInput,
    getFixture,
    mount,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { PortalFileInput } from "@project/project_sharing/components/portal_file_input/portal_file_input";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";

const serviceRegistry = registry.category("services");

let target;

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

async function createFileInput({ mockPost, mockAdd, props }) {
    serviceRegistry.add("notification", {
        start: () => ({
            add: mockAdd || (() => {}),
        }),
    });
    serviceRegistry.add("http", {
        start: () => ({
            post: mockPost || (() => {}),
        }),
    });
    const env = await makeTestEnv();
    await mount(PortalFileInput, target, { env, props });
}

// -----------------------------------------------------------------------------
// Tests
// -----------------------------------------------------------------------------

QUnit.module("Project", ({ beforeEach }) => {
    beforeEach(() => {
        patchWithCleanup(odoo, { csrf_token: "dummy" });

        target = getFixture();
    });

    QUnit.module("PortalComponents");

    QUnit.test("uploading a file that is too heavy in portal will send a notification", async (assert) => {
        serviceRegistry.add("localization", makeFakeLocalizationService());
        patchWithCleanup(session, { max_file_upload_size: 2 });
        await createFileInput({
            props: {
                onUpload(files) {
                    assert.deepEqual(files, [null]);
                },
            },
            mockAdd: (message) => {
                assert.step("notification");
                assert.strictEqual(
                    message,
                    "The selected file (4B) is larger than the maximum allowed file size (2B)."
                );
            },
        });

        const file = new File(["test"], "fake_file.txt", { type: "text/plain" });
        await editInput(target, ".o_file_input input", file);
        assert.verifySteps(
            ["notification"],
            "Only the notification will be triggered and the file won't be uploaded."
        );
    });
});
