/** @odoo-module **/

import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import {
    editInput,
    getFixture,
    mount,
    patchWithCleanup,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { FileInput } from "@web/core/file_input/file_input";
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
    await mount(FileInput, target, { env, props });
}

// -----------------------------------------------------------------------------
// Tests
// -----------------------------------------------------------------------------

QUnit.module("Components", ({ beforeEach }) => {
    beforeEach(() => {
        patchWithCleanup(odoo, { csrf_token: "dummy" });

        target = getFixture();
    });

    // This module cannot be tested as thoroughly as we want it to be:
    // browsers do not let scripts programmatically assign values to inputs
    // of type file
    QUnit.module("FileInput");

    QUnit.test("Upload a file: default props", async function (assert) {
        assert.expect(6);

        await createFileInput({
            mockPost: (route, params) => {
                assert.deepEqual(params, {
                    csrf_token: "dummy",
                    ufile: [],
                });
                assert.step(route);
                return "[]";
            },
            props: {},
        });
        const input = target.querySelector(".o_file_input input");

        assert.strictEqual(
            target.querySelector(".o_file_input").innerText.trim().toUpperCase(),
            "CHOOSE FILE",
            "File input total text should match its given inner element's text"
        );
        assert.strictEqual(input.accept, "*", "Input should accept all files by default");

        await triggerEvent(input, null, "change", {}, { skipVisibilityCheck: true });

        assert.notOk(input.multiple, "'multiple' attribute should not be set");
        assert.verifySteps(["/web/binary/upload_attachment"]);
    });

    QUnit.test("Upload a file: custom attachment", async function (assert) {
        assert.expect(6);

        await createFileInput({
            props: {
                acceptedFileExtensions: ".png",
                multiUpload: true,
                resId: 5,
                resModel: "res.model",
                route: "/web/binary/upload",
                onUpload(files) {
                    assert.strictEqual(
                        files.length,
                        0,
                        "'files' property should be an empty array"
                    );
                },
            },
            mockPost: (route, params) => {
                assert.deepEqual(params, {
                    id: 5,
                    model: "res.model",
                    csrf_token: "dummy",
                    ufile: [],
                });
                assert.step(route);
                return "[]";
            },
        });
        const input = target.querySelector(".o_file_input input");

        assert.strictEqual(input.accept, ".png", "Input should now only accept pngs");

        await triggerEvent(input, null, "change", {}, { skipVisibilityCheck: true });

        assert.ok(input.multiple, "'multiple' attribute should be set");
        assert.verifySteps(["/web/binary/upload"]);
    });

    QUnit.test("Hidden file input", async (assert) => {
        assert.expect(1);

        await createFileInput({
            props: { hidden: true },
        });

        assert.isNotVisible(target.querySelector(".o_file_input"));
    });

    QUnit.test("uploading a file that is too heavy will send a notification", async (assert) => {
        serviceRegistry.add("localization", makeFakeLocalizationService());
        patchWithCleanup(session, { max_file_upload_size: 2 });
        await createFileInput({
            props: {
                onUpload(files) {
                    // This code should be unreachable in this case
                    assert.step(files[0].name);
                },
            },
            mockPost: (route, params) => {
                return JSON.stringify([{ name: params.ufile[0].name }]);
            },
            mockAdd: (message) => {
                assert.step("notification");
                // Message is a bit weird because values (2 and 4 bytes) are simplified to 2 decimals in regards to megabytes
                assert.strictEqual(
                    message,
                    "The selected file (4B) is over the maximum allowed file size (2B)."
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
