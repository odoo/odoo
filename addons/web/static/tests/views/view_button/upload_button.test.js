import { expect, test } from "@odoo/hoot";
import { animationFrame, queryOne, setInputFiles } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    fields,
    getService,
    isSmall,
    mockService,
    mockUpload,
    models,
    mountView,
    mountWebClient,
    onRpc,
    patchWithCleanup,
    webModels,
} from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { session } from "@web/session";

class Foo extends models.Model {
    foo = fields.Char();
    _records = [
        { id: 1, foo: "yop" },
        { id: 2, foo: "blip" },
    ];
}
const { ResCompany, ResPartner, ResUsers } = webModels;
defineModels([Foo, ResCompany, ResPartner, ResUsers]);

/**
 * @param {Object|false|((params: Object) => any)} [result] the action returned
 *      by the method, or the function answering the requests
 * @returns {Object[]} the requests: their route and fields
 */
function mockFileUpload(result = false) {
    const uploads = [];
    mockUpload((route, params) => {
        uploads.push({ route, ...params });
        return typeof result === "function" ? result(params) : { result };
    });
    return uploads;
}

function fileDragEvent(type, files = []) {
    const ev = new Event(type, { bubbles: true, cancelable: true });
    Object.defineProperty(ev, "dataTransfer", { value: { types: ["Files"], files } });
    return ev;
}

async function clickUploadButton(name = "upload_it") {
    if (isSmall()) {
        await contains(".btn.dropdown-toggle").click();
    }
    await contains(`button[name=${name}]`).click();
}

const pdf = (name = "a.pdf", content = "x") =>
    new File([content], name, { type: "application/pdf" });

test("list view: an upload button asks for files and sends them to the method", async () => {
    const uploads = mockFileUpload();
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <header>
                    <button type="upload" name="upload_it" string="Upload"
                        options="{'accept': '.pdf'}" context="{'b': 2}"/>
                </header>
                <field name="foo"/>
            </list>`,
        context: { a: 1 },
    });
    await clickUploadButton();
    await animationFrame();
    // the input is hidden, so hoot selectors would not find it
    expect(document.querySelectorAll("input[type=file]")).toHaveLength(1);
    expect(document.querySelector("input[type=file]").accept).toBe(".pdf");

    await setInputFiles([pdf()]);
    await animationFrame();
    expect(document.querySelectorAll("input[type=file]")).toHaveLength(0);
    expect(uploads).toHaveLength(1);
    expect(uploads[0].route).toBe("/web/dataset/call_upload/foo/upload_it");
    expect(uploads[0].ufile.map((f) => f.name)).toEqual(["a.pdf"]);
    expect(uploads[0].res_ids).toBe("[]");
    expect(JSON.parse(uploads[0].context)).toMatchObject({ a: 1, b: 2 });
});

test.tags("desktop");
test("list view: the selected records are not given to the method", async () => {
    const uploads = mockFileUpload();
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <header>
                    <button type="upload" name="upload_it" string="Upload"
                        options="{'accept': '.pdf'}" context="{'b': 2}"/>
                </header>
                <field name="foo"/>
            </list>`,
    });
    await contains(".o_data_row:first .o_list_record_selector input").click();
    await contains("button[name=upload_it]").click();
    await setInputFiles([pdf()]);
    await animationFrame();
    expect(uploads[0].res_ids).toBe("[]");
    expect("active_ids" in JSON.parse(uploads[0].context)).toBe(false);
});

test.tags("desktop");
test("list view: an upload button shown for a selection is given the selected records", async () => {
    const uploads = mockFileUpload();
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <header>
                    <button type="upload" name="upload_it" string="Upload" display="selection"/>
                </header>
                <field name="foo"/>
            </list>`,
    });
    await contains(".o_data_row:eq(1) .o_list_record_selector input").click();
    await contains("button[name=upload_it]").click();
    await setInputFiles([pdf()]);
    await animationFrame();
    expect(uploads[0].res_ids).toBe("[2]");
});

test("upload button: cancelling the file picker uploads nothing", async () => {
    const uploads = mockFileUpload();
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <header>
                    <button type="upload" name="upload_it" string="Upload"
                        options="{'accept': '.pdf'}" context="{'b': 2}"/>
                </header>
                <field name="foo"/>
            </list>`,
    });
    await clickUploadButton();
    document.querySelector("input[type=file]").dispatchEvent(new Event("cancel"));
    await animationFrame();
    expect(document.querySelectorAll("input[type=file]")).toHaveLength(0);
    expect(uploads).toHaveLength(0);
});

test("upload button: the server action is executed", async () => {
    registry.category("actions").add("upload_next_action", (action) => {
        expect.step(`doAction ${action.tag}`);
    });
    mockFileUpload({ type: "ir.actions.client", tag: "upload_next_action" });
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <header>
                    <button type="upload" name="upload_it" string="Upload"
                        options="{'accept': '.pdf'}" context="{'b': 2}"/>
                </header>
                <field name="foo"/>
            </list>`,
    });
    await clickUploadButton();
    await setInputFiles([pdf()]);
    await animationFrame();
    expect.verifySteps(["doAction upload_next_action"]);
});

test("upload button: the error of the method is shown", async () => {
    mockFileUpload(() => ({
        error: {
            code: 0,
            message: "Odoo Server Error",
            data: { name: "odoo.exceptions.UserError", message: "Nope", debug: "" },
        },
    }));
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <header>
                    <button type="upload" name="upload_it" string="Upload"
                        options="{'accept': '.pdf'}" context="{'b': 2}"/>
                </header>
                <field name="foo"/>
            </list>`,
    });
    expect.errors(1);
    await clickUploadButton();
    await setInputFiles([pdf()]);
    await animationFrame();
    await animationFrame();
    expect.verifyErrors(["RPC_ERROR"]);
});

test("upload button: an error page of the server is shown", async () => {
    mockFileUpload(() => new Response("<h1>Request Entity Too Large</h1>", { status: 413 }));
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <header>
                    <button type="upload" name="upload_it" string="Upload"
                        options="{'accept': '.pdf'}" context="{'b': 2}"/>
                </header>
                <field name="foo"/>
            </list>`,
    });
    expect.errors(1);
    await clickUploadButton();
    await setInputFiles([pdf()]);
    await animationFrame();
    await animationFrame();
    expect.verifyErrors([/Request Entity Too Large/]);
});

test("upload button: files with an unaccepted type are ignored", async () => {
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
                    <button type="upload" name="upload_it" string="Upload"
                        options="{'accept': '.pdf'}" context="{'b': 2}"/>
                </header>
                <field name="foo"/>
            </list>`,
    });
    await clickUploadButton();
    await setInputFiles([pdf(), new File(["x"], "b.png", { type: "image/png" })]);
    await animationFrame();
    expect(uploads[0].ufile.map((f) => f.name)).toEqual(["a.pdf"]);
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
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <header>
                    <button type="upload" name="upload_it" string="Upload"
                        options="{'accept': '.pdf'}" context="{'b': 2}"/>
                </header>
                <field name="foo"/>
            </list>`,
    });
    await clickUploadButton();
    await setInputFiles([pdf("small.pdf"), pdf("big.pdf", "xxxx")]);
    await animationFrame();
    expect(uploads[0].ufile.map((f) => f.name)).toEqual(["small.pdf"]);
    expect.verifySteps([
        "These files are larger than the maximum upload size (2B) and were ignored: big.pdf",
    ]);
});

test("upload button: nothing is sent when the files together are too large", async () => {
    patchWithCleanup(session, { max_file_upload_size: 4 });
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
                    <button type="upload" name="upload_it" string="Upload"
                        options="{'accept': '.pdf'}" context="{'b': 2}"/>
                </header>
                <field name="foo"/>
            </list>`,
    });
    await clickUploadButton();
    await setInputFiles([pdf("a.pdf", "xxx"), pdf("b.pdf", "xxx")]);
    await animationFrame();
    expect(uploads).toHaveLength(0);
    expect.verifySteps(["The selected files (6B) are larger than the maximum upload size (4B)."]);
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
    await clickUploadButton();
    await setInputFiles([pdf("small.pdf"), pdf("big.pdf", "xxxx")]);
    await animationFrame();
    expect(uploads[0].ufile.map((f) => f.name)).toEqual(["small.pdf"]);
    expect.verifySteps([
        "These files are larger than the maximum upload size (2B) and were ignored: big.pdf",
    ]);
});

test.tags("desktop");
test("list view: a dropzone is shown over the content when dragging files", async () => {
    registry.category("actions").add("upload_next_action", (action) => {
        expect.step(`doAction ${action.tag}`);
    });
    const uploads = mockFileUpload({ type: "ir.actions.client", tag: "upload_next_action" });
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <list>
                <header>
                    <button type="upload" name="upload_it" string="Upload"
                        options="{'accept': '.pdf'}" context="{'b': 2}"/>
                </header>
                <field name="foo"/>
            </list>`,
        context: { a: 1 },
    });
    expect(".o-Dropzone").toHaveCount(0);

    document.dispatchEvent(fileDragEvent("dragenter"));
    await animationFrame();
    expect(".o-Dropzone").toHaveCount(1);
    expect(".o-Dropzone").toHaveText(/Drop files to upload them/);

    queryOne(".o-Dropzone").dispatchEvent(fileDragEvent("drop", [pdf()]));
    await animationFrame();
    await animationFrame();
    expect(".o-Dropzone").toHaveCount(0);
    expect(uploads).toHaveLength(1);
    expect(uploads[0].route).toBe("/web/dataset/call_upload/foo/upload_it");
    expect(JSON.parse(uploads[0].context)).toMatchObject({ a: 1, b: 2 });
    expect.verifySteps(["doAction upload_next_action"]);
});

test.tags("desktop");
test("list view: the dropped files are not uploaded when the edited row cannot be saved", async () => {
    const uploads = mockFileUpload();
    mockService("notification", {
        add(message) {
            expect.step(String(message));
        },
    });
    Foo._views = {
        list: `
            <list editable="bottom">
                <header>
                    <button type="upload" name="upload_it" string="Upload"/>
                </header>
                <field name="foo" required="1"/>
            </list>`,
    };
    await mountWebClient();
    await getService("action").doAction({
        res_model: "foo",
        type: "ir.actions.act_window",
        views: [[false, "list"]],
    });
    await contains(".o_data_cell").click();
    await contains(".o_field_widget[name=foo] input").clear();
    expect.verifySteps(["Missing required fields"]);
    document.dispatchEvent(fileDragEvent("dragenter"));
    await animationFrame();
    queryOne(".o-Dropzone").dispatchEvent(fileDragEvent("drop", [pdf()]));
    await animationFrame();
    expect.verifySteps([
        "Missing required fields",
        "The files were not uploaded: the changes could not be saved.",
    ]);
    expect(uploads).toHaveLength(0);
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
    expect(".o-Dropzone").toHaveCount(0);
});

test.tags("desktop");
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
    expect(".o-Dropzone").toHaveCount(1);
    expect(".o-Dropzone").toHaveText(/Drop files to upload them/);
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
    expect(".o-Dropzone").toHaveCount(0);

    await contains("button[name=upload_it]").click();
    await setInputFiles([new File(["x"], "a.txt")]);
    await animationFrame();
    expect(uploads[0].res_ids).toBe("[1]");
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
    expect(JSON.parse(uploads[0].res_ids)).toHaveLength(1);
});

test.todo("form view: the edits made during the upload are saved", async () => {
    const { promise, resolve } = Promise.withResolvers();
    mockFileUpload(() => promise);
    onRpc("web_save", ({ args }) => expect.step(`web_save ${JSON.stringify(args[1])}`));
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
    await contains("button[name=upload_it]").click();
    await setInputFiles([new File(["x"], "a.txt")]);
    await animationFrame();
    await contains(".o_field_widget[name=foo] input").edit("edited during the upload");

    expect.verifySteps([]);

    resolve({ result: false });
    await animationFrame();
    await animationFrame();
    expect.verifySteps(['web_save {"foo":"edited during the upload"}']);
    expect(".o_field_widget[name=foo] input").toHaveValue("edited during the upload");
    expect(".o_form_status_indicator_buttons").not.toBeVisible();
});

test.tags("desktop");
test("upload button (click): leaving the view during the upload notifies its end, without reload", async () => {
    const { promise, resolve } = Promise.withResolvers();
    mockFileUpload(() => promise);
    Foo._views = {
        list: `
        <list>
            <header>
                <button type="upload" name="upload_it" string="Upload"
                    options="{'accept': '.pdf'}" context="{'b': 2}"/>
            </header>
            <field name="foo"/>
        </list>`,
        kanban: `<kanban><templates><t t-name="card"><field name="foo"/></t></templates></kanban>`,
    };
    mockService("notification", {
        add(message, { buttons }) {
            expect.step(`${message} (${buttons.map((b) => b.name)})`);
        },
    });
    onRpc("web_search_read", () => {
        expect.step("web_search_read");
    });
    await mountWebClient();
    await getService("action").doAction({
        res_model: "foo",
        type: "ir.actions.act_window",
        views: [[false, "list"]],
    });
    await contains("button[name=upload_it]").click();
    await setInputFiles([pdf()]);
    await animationFrame();
    await getService("action").doAction({
        res_model: "foo",
        type: "ir.actions.act_window",
        views: [[false, "kanban"]],
    });
    expect.verifySteps(["web_search_read", "web_search_read"]);

    resolve({ result: false });
    await animationFrame();
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1);
    expect.verifySteps(["The files were uploaded. ()"]);
});

test("upload button (drop): leaving the view during the upload notifies its end, without reload", async () => {
    const { promise, resolve } = Promise.withResolvers();
    mockFileUpload(() => promise);
    Foo._views = {
        list: `
        <list>
            <header>
                <button type="upload" name="upload_it" string="Upload"
                    options="{'accept': '.pdf'}" context="{'b': 2}"/>
            </header>
            <field name="foo"/>
        </list>`,
        kanban: `<kanban><templates><t t-name="card"><field name="foo"/></t></templates></kanban>`,
    };
    mockService("notification", {
        add(message, { buttons }) {
            expect.step(`${message} (${buttons.map((b) => b.name)})`);
        },
    });
    onRpc("web_search_read", () => {
        expect.step("web_search_read");
    });
    await mountWebClient();
    await getService("action").doAction({
        res_model: "foo",
        type: "ir.actions.act_window",
        views: [[false, "list"]],
    });
    document.dispatchEvent(fileDragEvent("dragenter"));
    await animationFrame();
    queryOne(".o-Dropzone").dispatchEvent(fileDragEvent("drop", [pdf()]));
    await animationFrame();
    await getService("action").doAction({
        res_model: "foo",
        type: "ir.actions.act_window",
        views: [[false, "kanban"]],
    });
    expect.verifySteps(["web_search_read", "web_search_read"]);

    resolve({ result: false });
    await animationFrame();
    await animationFrame();
    expect(".o_kanban_view").toHaveCount(1);
    expect.verifySteps(["The files were uploaded. ()"]);
});
