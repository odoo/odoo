import { beforeEach, expect, test } from "@odoo/hoot";
import {
    contains,
    mockService,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { setInputFiles } from "@odoo/hoot-dom";
import { Deferred, animationFrame } from "@odoo/hoot-mock";
import { FileInput } from "@web/core/file_input/file_input";
import { session } from "@web/session";

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

async function createFileInput({ mockPost, mockAdd, props }) {
    mockService("notification", {
        add: mockAdd || (() => {}),
    });
    mockService("http", {
        post: mockPost || (() => {}),
    });
    await mountWithCleanup(FileInput, { props });
}

// -----------------------------------------------------------------------------
// Tests
// -----------------------------------------------------------------------------

beforeEach(() => {
    patchWithCleanup(odoo, { csrf_token: "dummy" });
});

test("Upload a file: default props", async () => {
    expect.assertions(5);

    await createFileInput({
        mockPost: (route, params) => {
            expect(params).toEqual({
                csrf_token: "dummy",
                ufile: [],
            });
            expect.step(route);
            return "[]";
        },
        props: {},
    });

    expect(".o_file_input").toHaveText("Choose File", {
        message: "File input total text should match its given inner element's text",
    });
    expect(".o_file_input input").toHaveAttribute("accept", "*", {
        message: "Input should accept all files by default",
    });

    await contains(".o_file_input input", { visible: false }).click();
    await setInputFiles([]);

    expect(".o_file_input input").not.toHaveAttribute("multiple", null, {
        message: "'multiple' attribute should not be set",
    });
    expect.verifySteps(["/web/binary/upload_attachment"]);
});

test("Upload a file: custom attachment", async () => {
    expect.assertions(5);

    await createFileInput({
        props: {
            acceptedFileExtensions: ".png",
            multiUpload: true,
            resId: 5,
            resModel: "res.model",
            route: "/web/binary/upload",
            onUpload(files) {
                expect(files).toHaveLength(0, {
                    message: "'files' property should be an empty array",
                });
            },
        },
        mockPost: (route, params) => {
            expect(params).toEqual({
                id: 5,
                model: "res.model",
                csrf_token: "dummy",
                ufile: [],
            });
            expect.step(route);
            return "[]";
        },
    });

    expect(".o_file_input input").toHaveAttribute("accept", ".png", {
        message: "Input should now only accept pngs",
    });

    await contains(".o_file_input input", { visible: false }).click();
    await setInputFiles([]);

    expect(".o_file_input input").toHaveAttribute("multiple", null, {
        message: "'multiple' attribute should be set",
    });

    expect.verifySteps(["/web/binary/upload"]);
});

test("Hidden file input", async () => {
    await createFileInput({
        props: { hidden: true },
    });

    expect(".o_file_input").not.toBeVisible();
});

test("uploading the same file twice triggers the onChange twice", async () => {
    await createFileInput({
        props: {
            onUpload(files) {
                expect.step(files[0].name);
            },
        },
        mockPost: (_, params) => {
            return JSON.stringify([{ name: params.ufile[0].name }]);
        },
    });

    const file = new File(["test"], "fake_file.txt", { type: "text/plain" });
    await contains(".o_file_input input", { visible: false }).click();
    await setInputFiles([file]);
    await animationFrame();
    expect.verifySteps(["fake_file.txt"]);

    await contains(".o_file_input input", { visible: false }).click();
    await setInputFiles([file]);
    await animationFrame();
    expect.verifySteps(["fake_file.txt"]);
});

test("uploading a file that is too heavy will send a notification", async () => {
    patchWithCleanup(session, { max_file_upload_size: 2 });
    await createFileInput({
        props: {
            onUpload(files) {
                // This code should be unreachable in this case
                expect.step(files[0].name);
            },
        },
        mockPost: (_, params) => {
            return JSON.stringify([{ name: params.ufile[0].name }]);
        },
        mockAdd: (message) => {
            expect.step("notification");
            // Message is a bit weird because values (2 and 4 bytes) are simplified to 2 decimals in regards to megabytes
            expect(message).toBe(
                "The selected file (4B) is larger than the maximum allowed file size (2B)."
            );
        },
    });

    const file = new File(["test"], "fake_file.txt", { type: "text/plain" });
    await contains(".o_file_input input", { visible: false }).click();
    await setInputFiles([file]);
    await animationFrame();
    expect.verifySteps(["notification"]);
});

test("Upload button is disabled if attachment upload is not finished", async () => {
    const uploadedPromise = new Deferred();
    await createFileInput({
        mockPost: async (route) => {
            if (route === "/web/binary/upload_attachment") {
                await uploadedPromise;
            }
            return "[]";
        },
        props: {},
    });
    //enable button
    await contains(".o_file_input input", { visible: false }).click();
    await setInputFiles([]);
    await animationFrame();

    //disable button
    expect(".o_file_input input").not.toBeEnabled({
        message: "the upload button should be disabled on upload",
    });

    uploadedPromise.resolve();
    await animationFrame();
    expect(".o_file_input input").toBeEnabled({
        message: "the upload button should be enabled for upload",
    });
});
