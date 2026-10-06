import { expect, test } from "@odoo/hoot";
import { animationFrame, queryOne, setInputFiles } from "@odoo/hoot-dom";
import { EventBus, proxy } from "@odoo/owl";
import {
    contains,
    defineModels,
    fields,
    getService,
    isSmall,
    mockService,
    models,
    mountView,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    webModels,
} from "@web/../tests/web_test_helpers";
import { session } from "@web/session";
import { filterFiles, uploadFiles } from "@web/views/view_button/upload_button";
import { UploadProgress } from "@web/views/view_button/upload_progress";

class Foo extends models.Model {
    foo = fields.Char();
    line_ids = fields.One2many({ relation: "line" });
    _records = [{ id: 1, foo: "yop" }];
}
class Line extends models.Model {
    name = fields.Char();
}
const { ResCompany, ResPartner, ResUsers } = webModels;
defineModels([Foo, Line, ResCompany, ResPartner, ResUsers]);

function mockFileUpload(result = false) {
    const bus = new EventBus();
    const uploads = [];
    mockService("file_upload", {
        bus,
        uploads: {},
        async upload(route, files, { buildFormData }) {
            const formData = new FormData();
            buildFormData(formData);
            const upload = { id: uploads.length + 1, state: "loaded", response: { result } };
            uploads.push({ route, files, formData });
            setTimeout(() => bus.trigger("FILE_UPLOAD_LOADED", { upload }));
            return upload;
        },
    });
    return uploads;
}

function fileDragEvent(type, files = []) {
    const ev = new Event(type, { bubbles: true, cancelable: true });
    Object.defineProperty(ev, "dataTransfer", { value: { types: ["Files"], files } });
    return ev;
}

const listArch = `
    <list>
        <header>
            <button type="upload" name="upload_it" string="Upload"
                options="{'accept': '.pdf'}" context="{'b': 2}"/>
        </header>
        <field name="foo"/>
    </list>`;

test("filterFiles keeps the files matching the accepted types", () => {
    const pdf = new File(["x"], "a.PDF", { type: "application/pdf" });
    const png = new File(["x"], "b.png", { type: "image/png" });
    const xml = new File(["x"], "c.xml", { type: "text/xml" });
    expect(filterFiles([pdf, png, xml], "").accepted).toEqual([pdf, png, xml]);
    expect(filterFiles([pdf, png, xml], ".pdf, .xml")).toEqual({
        accepted: [pdf, xml],
        rejected: [png],
    });
    expect(filterFiles([pdf, png, xml], "image/*").accepted).toEqual([png]);
    expect(filterFiles([pdf, png, xml], "application/pdf").accepted).toEqual([pdf]);
});

test("list view: an upload button asks for files and sends them to the method", async () => {
    const uploads = mockFileUpload();
    await mountView({ resModel: "foo", type: "list", arch: listArch, context: { a: 1 } });
    if (isSmall()) {
        await contains(".btn.dropdown-toggle").click();
    }
    await contains("button[name=upload_it]").click();
    await animationFrame();
    // the input is hidden, so hoot selectors would not find it
    expect(document.querySelectorAll("input[type=file]")).toHaveLength(1);
    expect(document.querySelector("input[type=file]").accept).toBe(".pdf");

    await setInputFiles([new File(["x"], "a.pdf", { type: "application/pdf" })]);
    await animationFrame();
    expect(document.querySelectorAll("input[type=file]")).toHaveLength(0);
    expect(uploads).toHaveLength(1);
    expect(uploads[0].route).toBe("/web/dataset/call_upload");
    expect(uploads[0].files.map((f) => f.name)).toEqual(["a.pdf"]);
    expect(uploads[0].formData.get("model")).toBe("foo");
    expect(uploads[0].formData.get("method")).toBe("upload_it");
    expect(uploads[0].formData.get("res_ids")).toBe("[]");
    expect(JSON.parse(uploads[0].formData.get("context"))).toMatchObject({ a: 1, b: 2 });
});

test("upload button: the server action is executed", async () => {
    const action = { type: "ir.actions.act_window", res_model: "foo" };
    mockFileUpload(action);
    mockService("action", {
        doAction(result) {
            expect.step(`doAction ${result.res_model}`);
        },
    });
    await mountView({ resModel: "foo", type: "list", arch: listArch });
    if (isSmall()) {
        await contains(".btn.dropdown-toggle").click();
    }
    await contains("button[name=upload_it]").click();
    await setInputFiles([new File(["x"], "a.pdf", { type: "application/pdf" })]);
    await animationFrame();
    expect.verifySteps(["doAction foo"]);
});

test("upload button: the notifications of the returned action are displayed", async () => {
    mockFileUpload({
        type: "ir.actions.act_window",
        res_model: "foo",
        context: { notifications: { "a.pdf": "Imported" } },
    });
    mockService("notification", {
        add(message, options) {
            expect.step(`${options.title}: ${message}`);
        },
    });
    mockService("action", {
        doAction(result) {
            expect.step(`doAction ${JSON.stringify(result.context)}`);
        },
    });
    await mountView({ resModel: "foo", type: "list", arch: listArch });
    if (isSmall()) {
        await contains(".btn.dropdown-toggle").click();
    }
    await contains("button[name=upload_it]").click();
    await setInputFiles([new File(["x"], "a.pdf", { type: "application/pdf" })]);
    await animationFrame();
    expect.verifySteps(["a.pdf: Imported", "doAction {}"]);
});

test("upload button: files with an unaccepted type are ignored", async () => {
    const uploads = mockFileUpload();
    mockService("notification", {
        add(message) {
            expect.step(message);
        },
    });
    await mountView({ resModel: "foo", type: "list", arch: listArch });
    if (isSmall()) {
        await contains(".btn.dropdown-toggle").click();
    }
    await contains("button[name=upload_it]").click();
    await setInputFiles([
        new File(["x"], "a.pdf", { type: "application/pdf" }),
        new File(["x"], "b.png", { type: "image/png" }),
    ]);
    await animationFrame();
    expect(uploads[0].files.map((f) => f.name)).toEqual(["a.pdf"]);
    expect.verifySteps(["These files have an invalid type and were ignored: b.png"]);
});

test("upload button: files too large are ignored, the others are uploaded", async () => {
    patchWithCleanup(session, { max_file_upload_size: 2 });
    const uploads = mockFileUpload();
    mockService("notification", {
        add(message) {
            expect.step(message);
        },
    });
    await mountView({ resModel: "foo", type: "list", arch: listArch });
    if (isSmall()) {
        await contains(".btn.dropdown-toggle").click();
    }
    await contains("button[name=upload_it]").click();
    await setInputFiles([
        new File(["x"], "small.pdf", { type: "application/pdf" }),
        new File(["xxxx"], "big.pdf", { type: "application/pdf" }),
    ]);
    await animationFrame();
    expect(uploads[0].files.map((f) => f.name)).toEqual(["small.pdf"]);
    expect.verifySteps([
        "The selected file (4B) is larger than the maximum allowed file size (2B).",
    ]);
});

test("upload button: options.max_size limits the size of the files", async () => {
    const uploads = mockFileUpload();
    mockService("notification", {
        add(message) {
            expect.step(message);
        },
    });
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <header>
                    <button type="upload" name="upload_it" string="Upload" options="{'max_size': 2}"/>
                </header>
                <field name="foo"/>
            </list>`,
    });
    if (isSmall()) {
        await contains(".btn.dropdown-toggle").click();
    }
    await contains("button[name=upload_it]").click();
    await setInputFiles([
        new File(["x"], "small.pdf", { type: "application/pdf" }),
        new File(["xxxx"], "big.pdf", { type: "application/pdf" }),
    ]);
    await animationFrame();
    expect(uploads[0].files.map((f) => f.name)).toEqual(["small.pdf"]);
    expect.verifySteps([
        "The selected file (4B) is larger than the maximum allowed file size (2B).",
    ]);
});

test("list view: a dropzone is shown over the content when dragging files", async () => {
    const uploads = mockFileUpload();
    await mountView({ resModel: "foo", type: "list", arch: listArch });
    expect(".o-UploadDropzone").toHaveCount(0);

    document.dispatchEvent(fileDragEvent("dragenter"));
    await animationFrame();
    expect(".o-UploadDropzone").toHaveCount(1);
    expect(".o-UploadDropzone").toHaveText("Drop files to upload them to");

    queryOne(".o-UploadDropzone").dispatchEvent(
        fileDragEvent("drop", [new File(["x"], "a.pdf", { type: "application/pdf" })])
    );
    await animationFrame();
    expect(".o-UploadDropzone").toHaveCount(0);
    expect(uploads).toHaveLength(1);
    expect(uploads[0].formData.get("method")).toBe("upload_it");
});

test("list view: no dropzone when the upload button is invisible", async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <header>
                    <button type="upload" name="upload_it" string="Upload" invisible="1"/>
                </header>
                <field name="foo"/>
            </list>`,
    });
    document.dispatchEvent(fileDragEvent("dragenter"));
    await animationFrame();
    expect(".o-UploadDropzone").toHaveCount(0);
});

test("kanban view: an upload button comes with a dropzone", async () => {
    mockFileUpload();
    await mountView({
        resModel: "foo",
        type: "kanban",
        arch: `
            <kanban>
                <header>
                    <button type="upload" name="upload_it" string="Upload"/>
                </header>
                <templates>
                    <t t-name="card"><field name="foo"/></t>
                </templates>
            </kanban>`,
    });
    document.dispatchEvent(fileDragEvent("dragenter"));
    await animationFrame();
    expect(".o-UploadDropzone").toHaveCount(1);
    expect(".o-UploadDropzone").toHaveText("Drop files to upload them to");
});

test("kanban view: the card with an upload button is the dropzone", async () => {
    const uploads = mockFileUpload();
    await mountView({
        resModel: "foo",
        type: "kanban",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                        <button type="upload" name="upload_it" string="Upload"/>
                    </t>
                </templates>
            </kanban>`,
    });
    document.dispatchEvent(fileDragEvent("dragenter"));
    await animationFrame();
    expect(".o-UploadDropzone").toHaveCount(1);
    expect(".o-UploadDropzone").toHaveText(/Drop files to upload them to/);

    queryOne(".o-UploadDropzone").dispatchEvent(
        fileDragEvent("drop", [new File(["x"], "a.pdf", { type: "application/pdf" })])
    );
    await animationFrame();
    expect(uploads).toHaveLength(1);
    expect(uploads[0].formData.get("res_ids")).toBe("[1]");
});

test("form view: an upload button has no dropzone", async () => {
    const uploads = mockFileUpload();
    await mountView({
        resModel: "foo",
        type: "form",
        resId: 1,
        arch: `
            <form>
                <header>
                    <button type="upload" name="upload_it" string="Upload"/>
                </header>
                <field name="foo"/>
            </form>`,
    });
    document.dispatchEvent(fileDragEvent("dragenter"));
    await animationFrame();
    expect(".o-UploadDropzone").toHaveCount(0);

    await contains("button[name=upload_it]").click();
    await setInputFiles([new File(["x"], "a.txt")]);
    await animationFrame();
    expect(uploads[0].formData.get("res_ids")).toBe("[1]");
});

test("upload progress: the uploads of the buttons are shown until they are processed", async () => {
    const bus = new EventBus();
    const upload = proxy({ id: 1, state: "loading", progress: 0.5, title: "bill.pdf" });
    mockService("file_upload", { bus, uploads: {}, upload: async () => upload });
    await mountWithCleanup(UploadProgress);
    expect(".o_upload_progress").toHaveCount(0);

    const services = {
        file_upload: getService("file_upload"),
        notification: getService("notification"),
    };
    const done = uploadFiles(services, {
        clickParams: { name: "upload_it" },
        resModel: "foo",
        files: [new File(["x"], "bill.pdf")],
    });
    await animationFrame();
    expect(".o_upload_progress").toHaveText("Uploading bill.pdf");
    upload.progress = 1;
    await animationFrame();
    expect(".o_upload_progress").toHaveText("Processing bill.pdf");

    upload.state = "loaded";
    bus.trigger("FILE_UPLOAD_LOADED", { upload });
    await done;
    await animationFrame();
    expect(".o_upload_progress").toHaveCount(0);
});

test("list view: a dropzone_only button gives the dropzone, not a button", async () => {
    const uploads = mockFileUpload();
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <header>
                    <button type="upload" name="upload_it" string="Upload" options="{'dropzone_only': True}"/>
                </header>
                <field name="foo"/>
            </list>`,
    });
    expect("button[name=upload_it]").toHaveCount(0);

    document.dispatchEvent(fileDragEvent("dragenter"));
    await animationFrame();
    queryOne(".o-UploadDropzone").dispatchEvent(
        fileDragEvent("drop", [new File(["x"], "a.pdf", { type: "application/pdf" })])
    );
    await animationFrame();
    expect(uploads).toHaveLength(1);
    expect(uploads[0].formData.get("method")).toBe("upload_it");

    if (!isSmall()) {
        // nor in the actions of the selection
        await contains(".o_data_row .o_list_record_selector input").click();
        expect("button[name=upload_it]").toHaveCount(0);
    }
});

test("kanban view: a dropzone_only button in a card is hidden, the card is the dropzone", async () => {
    const uploads = mockFileUpload();
    await mountView({
        resModel: "foo",
        type: "kanban",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                        <button type="upload" name="upload_it" string="Upload" options="{'dropzone_only': True}"/>
                    </t>
                </templates>
            </kanban>`,
    });
    expect("button[name=upload_it]").not.toBeVisible();

    document.dispatchEvent(fileDragEvent("dragenter"));
    await animationFrame();
    queryOne(".o-UploadDropzone").dispatchEvent(
        fileDragEvent("drop", [new File(["x"], "a.pdf", { type: "application/pdf" })])
    );
    await animationFrame();
    expect(uploads).toHaveLength(1);
    expect(uploads[0].formData.get("res_ids")).toBe("[1]");
});

test("form view: the record is saved before the upload", async () => {
    const uploads = mockFileUpload();
    onRpc("web_save", () => expect.step("web_save"));
    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <header>
                    <button type="upload" name="upload_it" string="Upload"/>
                </header>
                <field name="foo"/>
            </form>`,
    });
    await contains(".o_field_widget[name=foo] input").edit("new");
    await contains("button[name=upload_it]").click();
    await setInputFiles([new File(["x"], "a.txt")]);
    await animationFrame();
    expect.verifySteps(["web_save"]);
    expect(JSON.parse(uploads[0].formData.get("res_ids"))).toHaveLength(1);
});

test("form view: options.model calls the method of that model, with the button context", async () => {
    const uploads = mockFileUpload();
    onRpc("web_save", () => expect.step("web_save"));
    await mountView({
        resModel: "foo",
        type: "form",
        resId: 1,
        arch: `
            <form>
                <header>
                    <button type="upload" name="upload_it" string="Upload"
                        options="{'model': 'bar'}" context="{'default_foo': foo}"/>
                </header>
                <field name="foo"/>
            </form>`,
    });
    await contains(".o_field_widget[name=foo] input").edit("new");
    await contains("button[name=upload_it]").click();
    await setInputFiles([new File(["x"], "a.pdf")]);
    await animationFrame();
    expect.verifySteps([]);
    expect(uploads[0].formData.get("model")).toBe("bar");
    expect(uploads[0].formData.get("res_ids")).toBe("[]");
    expect(JSON.parse(uploads[0].formData.get("context"))).toMatchObject({ default_foo: "new" });
});

test("form view: an upload button in the header of an x2many calls the comodel, without saving", async () => {
    const uploads = mockFileUpload();
    onRpc("web_save", () => expect.step("web_save"));
    await mountView({
        resModel: "foo",
        type: "form",
        resId: 1,
        arch: `
            <form>
                <field name="foo"/>
                <field name="line_ids">
                    <list>
                        <header>
                            <button type="upload" name="upload_lines" string="Upload lines"/>
                        </header>
                        <field name="name"/>
                    </list>
                </field>
            </form>`,
    });
    await contains(".o_field_widget[name=foo] input").edit("new");
    await contains(".o_field_x2many .o_cp_buttons button[name=upload_lines]").click();
    await setInputFiles([new File(["x"], "a.pdf")]);
    await animationFrame();
    expect.verifySteps([]);
    expect(uploads[0].formData.get("model")).toBe("line");
    expect(uploads[0].formData.get("method")).toBe("upload_lines");
    expect(JSON.parse(uploads[0].formData.get("context"))).toMatchObject({
        active_model: "foo",
        active_id: 1,
    });
});
