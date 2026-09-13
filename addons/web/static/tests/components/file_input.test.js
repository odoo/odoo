// @ts-check

import { beforeEach, expect, test } from "@odoo/hoot";
import { setInputFiles } from "@odoo/hoot-dom";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import {
    contains,
    mockService,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { FileInput } from "@web/components/file_input/file_input";
import { session } from "@web/session";

/**
 * @param {{
 *     mockPost?: (route: string, params: Record<string, any>) => any,
 *     mockAdd?: (...args: any[]) => any,
 *     props: Partial<import("@web/components/file_input/file_input").FileInputProps>,
 * }} options
 */
async function createFileInput({ mockPost, mockAdd, props }) {
    mockService("notification", {
        add: mockAdd || (() => {}),
    });
    mockService("http", {
        post: mockPost || (() => {}),
    });
    return mountWithCleanup(FileInput, { props });
}

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
        mockPost: (_, params) => JSON.stringify([{ name: params.ufile[0].name }]),
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
                expect.step(files[0].name);
            },
        },
        mockPost: (_, params) => JSON.stringify([{ name: params.ufile[0].name }]),
        mockAdd: (message) => {
            expect.step("notification");
            expect(message).toBe(
                "The selected file (4B) is larger than the maximum allowed file size (2B).",
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
    await contains(".o_file_input input", { visible: false }).click();
    await setInputFiles([]);
    await animationFrame();

    expect(".o_file_input input").not.toBeEnabled({
        message: "the upload button should be disabled on upload",
    });

    uploadedPromise.resolve();
    await animationFrame();
    expect(".o_file_input input").toBeEnabled({
        message: "the upload button should be enabled for upload",
    });
});

test("a rejecting onWillUploadFiles still clears the input value (same-file retry)", async () => {
    expect.errors(1);
    await createFileInput({
        props: {
            onWillUploadFiles() {
                expect.step("rejected");
                throw new Error("invalid file");
            },
        },
        mockPost: (route, params) => JSON.stringify([{ name: params.ufile[0].name }]),
    });

    const input = /** @type {HTMLInputElement} */ (
        document.querySelector(".o_file_input input")
    );
    await contains(".o_file_input input", { visible: false }).click();
    await setInputFiles([new File(["test"], "fake_file.txt", { type: "text/plain" })]);
    await animationFrame();

    expect.verifySteps(["rejected"]);
    expect(input.value).toBe("", {
        message: "input value must be reset even when the pre-upload hook rejects",
    });
    expect(".o_file_input input").toBeEnabled({
        message: "the upload button must be re-enabled after a pre-upload rejection",
    });
    expect.verifyErrors(["invalid file"]);
});

test("support preprocessing of files via props", async () => {
    await createFileInput({
        props: {
            onWillUploadFiles(files) {
                expect.step(files[0].name);
                return files;
            },
        },
        mockPost: (route, params) => JSON.stringify([{ name: params.ufile[0].name }]),
    });

    await contains(".o_file_input input", { visible: false }).click();
    await setInputFiles([new File(["test"], "fake_file.txt", { type: "text/plain" })]);
    await animationFrame();

    expect.verifySteps(["fake_file.txt"]);
});

test("onUpload receives the files that were uploaded, not the ones that were picked", async () => {
    const resized = new File(["tiny"], "icon.png", { type: "image/png" });
    await createFileInput({
        props: {
            route: "/web/binary/upload",
            onWillUploadFiles: () => [resized],
            onUpload(_data, files) {
                expect(files).toEqual([resized]);
                expect.step("uploaded");
            },
        },
        mockPost: (_route, params) => {
            expect(params.ufile).toEqual([resized]);
            expect.step("posted");
            return "[]";
        },
    });
    await contains(".o_file_input input", { visible: false }).click();
    await setInputFiles([new File(["big"], "photo.png", { type: "image/png" })]);
    expect.verifySteps(["posted", "uploaded"]);
});

for (const reject of [false, true]) {
    test(`upload remains busy until its ${reject ? "rejected" : "successful"} consumer finishes`, async () => {
        const linking = new Deferred();
        // A detached callback rejection must not hide the completion assertion.
        linking.catch(() => {});
        const input = await createFileInput({
            mockPost: () => "[]",
            props: { onUpload: () => linking },
        });
        let outcome = "pending";
        const upload = input.onFileInputChange().then(
            () => {
                outcome = "resolved";
            },
            () => {
                outcome = "rejected";
            },
        );
        await animationFrame();
        expect(outcome).toBe("pending");
        expect(".o_file_input input").not.toBeEnabled();
        if (reject) {
            linking.reject(new Error("linking failed"));
        } else {
            linking.resolve();
        }
        await upload;
        await animationFrame();
        expect(outcome).toBe(reject ? "rejected" : "resolved");
        expect(".o_file_input input").toBeEnabled();
    });
}

test("a second change cannot post the same selection while upload is pending", async () => {
    const pending = new Deferred();
    const file = new File(["test"], "attachment.txt", { type: "text/plain" });
    const input = await createFileInput({
        mockPost: async (_route, params) => {
            expect(params.ufile).toEqual([file]);
            expect.step("post");
            await pending;
            return "[]";
        },
        props: { onUpload: () => expect.step("uploaded") },
    });
    const selection = new DataTransfer();
    selection.items.add(file);
    input.fileInputRef.el.files = selection.files;
    const first = input.onFileInputChange();
    const second = input.onFileInputChange();
    await animationFrame();
    expect.verifySteps(["post"]);
    pending.resolve();
    await Promise.all([first, second]);
    expect.verifySteps(["uploaded"]);
    expect(input.state.isDisable).toBe(false);
});
