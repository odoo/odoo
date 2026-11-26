import { expect, test } from "@odoo/hoot";
import { advanceTime, animationFrame } from "@odoo/hoot-mock";
import {
    contains,
    getService,
    mockService,
    mockUpload,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { FileUploadPlugin } from "@web/core/file_upload/file_upload_plugin";
import { UploadProgress } from "@web/core/file_upload/upload_progress";
import { session } from "@web/session";

const file = (name = "a.txt") => new File(["x"], name);

test("sendFiles: the upload is shown until a while after it ends", async () => {
    const { promise, resolve } = Promise.withResolvers();
    onRpc("/test/", () => promise);
    await mountWithCleanup(UploadProgress);
    const done = getService(FileUploadPlugin).sendFiles("/test/", { ufile: [file()], foo: "bar" });
    await animationFrame();
    expect(".o_upload_progress").toHaveText("Uploading a.txt");

    resolve({ ok: true });
    expect(await done).toEqual({ ok: true });
    await animationFrame();
    expect(".o_upload_progress").toHaveText("Uploaded a.txt");

    await advanceTime(3000);
    expect(".o_upload_progress").toHaveCount(0);
});

test("sendFiles: the fields are posted with the files", async () => {
    await mountWithCleanup(UploadProgress);
    onRpc("/test/", async (request) => {
        const body = await request.formData();
        expect.step(`${body.getAll("ufile").map((f) => f.name)} ${body.get("foo")}`);
        return {};
    });
    await getService(FileUploadPlugin).sendFiles("/test/", {
        ufile: [file("a.txt"), file("b.txt")],
        foo: "bar",
    });
    expect.verifySteps(["a.txt,b.txt bar"]);
});

test("sendFiles: only the files of the accepted types are sent", async () => {
    mockUpload((route, { ufile }) => {
        expect.step(ufile.map((f) => f.name).join(","));
        return {};
    });
    await mountWithCleanup(UploadProgress);
    const pdf = new File(["x"], "a.PDF", { type: "application/pdf" });
    const png = new File(["x"], "b.png", { type: "image/png" });
    const xml = new File(["x"], "c.xml", { type: "text/xml" });
    const fileUpload = getService(FileUploadPlugin);
    await fileUpload.sendFiles("/test/", { ufile: [pdf, png, xml] }, { accept: ".pdf, .xml" });
    await fileUpload.sendFiles("/test/", { ufile: [pdf, png, xml] }, { accept: "image/*" });
    await fileUpload.sendFiles("/test/", { ufile: [pdf, png, xml] }, { accept: "application/pdf" });
    expect.verifySteps(["a.PDF,c.xml", "b.png", "a.PDF"]);
});

test("sendFiles: the upload can be cancelled from its card", async () => {
    mockUpload(() => new Promise(() => {}));
    mockService("dialog", {
        add(Component, { confirm }) {
            confirm();
        },
    });
    await mountWithCleanup(UploadProgress);
    const done = getService(FileUploadPlugin).sendFiles("/test/", { ufile: [file()] });
    await animationFrame();
    await contains(".o-file-upload-progress-bar-abort", { visible: false }).click();
    expect(await done).toBe(null);
    await animationFrame();
    expect(".o_upload_progress").toHaveCount(0);
});

test("sendFiles: the upload can be cancelled with a signal", async () => {
    mockUpload(() => new Promise(() => {}));
    await mountWithCleanup(UploadProgress);
    const controller = new AbortController();
    const done = getService(FileUploadPlugin).sendFiles(
        "/test/",
        { ufile: [file()] },
        { signal: controller.signal }
    );
    await animationFrame();
    expect(".o_upload_progress").toHaveText("Uploading a.txt");

    controller.abort();
    expect(await done).toBe(null);
    await animationFrame();
    expect(".o_upload_progress").toHaveCount(0);
});

test("sendFiles: an error message of the server is thrown", async () => {
    await mountWithCleanup(UploadProgress);
    onRpc("/test/", () => ({ error: "Not allowed" }));
    await expect(
        getService(FileUploadPlugin).sendFiles("/test/", { ufile: [file()] })
    ).rejects.toThrow("Not allowed");
});

test("sendFiles: nothing is sent when the files together are too large", async () => {
    await mountWithCleanup(UploadProgress);
    patchWithCleanup(session, { max_file_upload_size: 1 });
    onRpc("/test/", () => expect.step("sent"));
    mockService("notification", {
        add(message) {
            expect.step(message);
        },
    });
    const result = await getService(FileUploadPlugin).sendFiles("/test/", {
        ufile: [file("a.txt"), file("b.txt")],
    });
    expect(result).toBe(null);
    expect.verifySteps(["The selected files (2B) are larger than the maximum upload size (1B)."]);
});

test("sendFiles: an error page of the server is thrown", async () => {
    await mountWithCleanup(UploadProgress);
    onRpc("/test/", () => new Response("<p>Boom HTML</p>", { status: 500 }));
    await expect(
        getService(FileUploadPlugin).sendFiles("/test/", { ufile: [file()] })
    ).rejects.toThrow("Boom HTML");
});

test("sendFiles: an error of the server is thrown as an RPC error", async () => {
    await mountWithCleanup(UploadProgress);
    onRpc("/test/", () => ({
        error: {
            code: 0,
            message: "Odoo Server Error",
            data: { name: "odoo.exceptions.ValidationError", message: "Boom Odoo" },
        },
    }));
    let error;
    try {
        await getService(FileUploadPlugin).sendFiles("/test/", { ufile: [file()] });
    } catch (e) {
        error = e;
    }
    expect(error.exceptionName).toBe("odoo.exceptions.ValidationError");
    expect(error.data.message).toBe("Boom Odoo");
});
