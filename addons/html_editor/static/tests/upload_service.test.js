import { animationFrame, expect, test } from "@odoo/hoot";
import { delay, click, queryOne } from "@odoo/hoot-dom";
import {
    defineModels,
    fields,
    getService,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

class Test extends models.Model {
    name = fields.Char();
    txt = fields.Html();
    _records = [{ id: 1, name: "Test", txt: "<p><br></p>" }];
}

defineModels([Test]);

test("should be able to cancel a file upload", async () => {
    onRpc("/html_editor/attachment/add_data", async (request) => {
        const { params } = await request.json();
        await delay(1000); // Delay to keep progressbar visible longer
        return {
            name: params.name,
        };
    });

    await mountView({
        type: "form",
        resId: 1,
        resModel: "test",
        arch: `
            <form>
                <field name="name"/>
                <field name="txt" widget="html"/>
            </form>`,
    });

    const fileUploadService = await getService("upload");
    let xhr;
    const waitForRequest = new Promise((res) => {
        patchWithCleanup(XMLHttpRequest.prototype, {
            open() {
                xhr = this;
                super.open(...arguments);
                res();
            },
            abort() {
                xhr.dispatchEvent(new Event("abort"));
                super.abort();
            },
        });
    });

    const file = new File(["test"], "fake_file.txt", { type: "text/plain", size: 100 });
    const uploadedFiles = [];
    const fileUploadProm = fileUploadService.uploadFiles(
        [file],
        { resModel: "test", resId: 1 },
        ({ name }) => {
            uploadedFiles.push(name);
        }
    );
    await animationFrame();
    expect(".o_we_progressbar").toHaveCount(1);
    await waitForRequest;
    const progressEv = new Event("progress");
    progressEv.loaded = 40;
    progressEv.total = 100;
    xhr.upload.dispatchEvent(progressEv);
    await animationFrame();
    expect(queryOne(".o_we_progressbar .progress-bar").style.width).toBe("40%");
    await click(".o_notification_indicator .fa-trash");
    await animationFrame();
    expect(".o_we_progressbar").toHaveCount(0);
    await fileUploadProm;
    expect(uploadedFiles.length).toBe(0);
});

test("should be able to cancel a file when uploading multiple files", async () => {
    onRpc("/html_editor/attachment/add_data", async (request) => {
        const { params } = await request.json();
        await delay(500);
        return {
            name: `${params.name}`,
        };
    });

    await mountView({
        type: "form",
        resId: 1,
        resModel: "test",
        arch: `
            <form>
                <field name="name"/>
                <field name="txt" widget="html"/>
            </form>`,
    });

    const fileUploadService = await getService("upload");
    const files = [
        new File(["test1"], "fake_file1.txt", { type: "text/plain", size: 100 }),
        new File(["test2"], "fake_file2.txt", { type: "text/plain", size: 200 }),
        new File(["test3"], "fake_file3.txt", { type: "text/plain", size: 300 }),
    ];
    const uploadedFiles = [];
    const fileUploadProm = fileUploadService.uploadFiles(
        files,
        { resModel: "test", resId: 1 },
        ({ name }) => {
            uploadedFiles.push(name);
        }
    );
    await animationFrame();
    expect(".o_we_progressbar").toHaveCount(3);
    await click(".o_we_progressbar:nth-child(2) .fa-trash"); // Delete 2nd file
    await animationFrame();
    expect(".o_we_progressbar").toHaveCount(2);
    await fileUploadProm;
    expect(uploadedFiles).toMatchObject(["fake_file1.txt", "fake_file3.txt"]);
});
