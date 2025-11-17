import { after, expect, test } from "@odoo/hoot";
import { click, queryOne, queryValue, setInputFiles, waitFor } from "@odoo/hoot-dom";
import { Deferred, animationFrame } from "@odoo/hoot-mock";
import {
    clickSave,
    contains,
    defineModels,
    fields,
    makeServerError,
    models,
    mountView,
    onRpc,
    pagerNext,
} from "@web/../tests/web_test_helpers";

import { toBase64Length } from "@web/core/utils/binary";
import { MAX_FILENAME_SIZE_BYTES } from "@web/views/fields/binary/binary_field";

const BINARY_FILE =
    "R0lGODlhDAAMAKIFAF5LAP/zxAAAANyuAP/gaP///wAAAAAAACH5BAEAAAUALAAAAAAMAAwAAAMlWLPcGjDKFYi9lxKBOaGcF35DhWHamZUW0K4mAbiwWtuf0uxFAgA7";

class Partner extends models.Model {
    _name = "res.partner";

    foo = fields.Char({ default: "My little Foo Value" });
    document = fields.Binary();
    product_id = fields.Many2one({ relation: "product" });

    _records = [{ foo: "coucou.txt", document: "coucou==\n" }];
}

class Product extends models.Model {
    name = fields.Char();

    _records = [
        { id: 37, name: "xphone" },
        { id: 41, name: "xpad" },
    ];
}

defineModels([Partner, Product]);

onRpc("has_group", () => true);

test("BinaryField is correctly rendered (readonly)", async () => {
    onRpc("/web/content", async (request) => {
        expect.step("/web/content");

        const body = await request.formData();
        expect(body).toBeInstanceOf(FormData);
        expect(body.get("field")).toBe("document", {
            message: "we should download the field document",
        });
        expect(body.get("data")).toBe("coucou==\n", {
            message: "we should download the correct data",
        });

        return new Blob([body.get("data")], { type: "text/plain" });
    });

    await mountView({
        resModel: "res.partner",
        resId: 1,
        type: "form",
        arch: `
            <form edit="0">
                <field name="document" filename="foo"/>
                <field name="foo"/>
            </form>
        `,
    });

    expect(`.o_field_widget[name="document"] a > .fa-download`).toHaveCount(1, {
        message: "the binary field should be rendered as a downloadable link in readonly",
    });
    expect(`.o_field_widget[name="document"]`).toHaveText("coucou.txt", {
        message: "the binary field should display the name of the file in the link",
    });
    expect(`.o_field_char`).toHaveText("coucou.txt", {
        message: "the filename field should have the file name as value",
    });

    // Testing the download button in the field
    // We must avoid the browser to download the file effectively
    const deferred = new Deferred();
    const downloadOnClick = (ev) => {
        const target = ev.target;
        if (target.tagName === "A" && "download" in target.attributes) {
            ev.preventDefault();
            document.removeEventListener("click", downloadOnClick);
            deferred.resolve();
        }
    };
    document.addEventListener("click", downloadOnClick);
    after(() => document.removeEventListener("click", downloadOnClick));

    await contains(`.o_field_widget[name="document"] a`).click();
    await deferred;
    expect.verifySteps(["/web/content"]);
});

test("BinaryField is correctly rendered", async () => {
    onRpc("/web/content", async (request) => {
        expect.step("/web/content");

        const body = await request.formData();
        expect(body).toBeInstanceOf(FormData);
        expect(body.get("field")).toBe("document", {
            message: "we should download the field document",
        });
        expect(body.get("data")).toBe("coucou==\n", {
            message: "we should download the correct data",
        });

        return new Blob([body.get("data")], { type: "text/plain" });
    });

    await mountView({
        resModel: "res.partner",
        resId: 1,
        type: "form",
        arch: `
            <form>
                <field name="document" filename="foo"/>
                <field name="foo"/>
            </form>
        `,
    });

    expect(`.o_field_widget[name="document"] a > .fa-download`).toHaveCount(0, {
        message: "the binary field should not be rendered as a downloadable link in edit",
    });
    expect(`.o_field_widget[name="document"].o_field_binary .o_input`).toHaveValue("coucou.txt", {
        message: "the binary field should display the file name in the input edit mode",
    });
    expect(`.o_field_binary .o_clear_file_button`).toHaveCount(1, {
        message: "there shoud be a button to clear the file",
    });
    expect(`.o_field_char input`).toHaveValue("coucou.txt", {
        message: "the filename field should have the file name as value",
    });

    // Testing the download button in the field
    // We must avoid the browser to download the file effectively
    const deferred = new Deferred();
    const downloadOnClick = (ev) => {
        const target = ev.target;
        if (target.tagName === "A" && "download" in target.attributes) {
            ev.preventDefault();
            document.removeEventListener("click", downloadOnClick);
            deferred.resolve();
        }
    };
    document.addEventListener("click", downloadOnClick);
    after(() => document.removeEventListener("click", downloadOnClick));

    await click(`.fa-download`);
    await deferred;
    expect.verifySteps(["/web/content"]);

    await click(`.o_field_binary .o_clear_file_button`);
    await animationFrame();
    expect(`.o_field_binary input`).not.toBeVisible({ message: "the input should be hidden" });
    expect(`.o_field_binary .o_select_file_button`).toHaveCount(1, {
        message: "there should be a button to upload the file",
    });
    expect(`.o_field_char input`).toHaveValue("", {
        message: "the filename field should be empty since we removed the file",
    });

    await clickSave();
    expect(`.o_field_widget[name="document"] a > .fa-download`).toHaveCount(0, {
        message:
            "the binary field should not render as a downloadable link since we removed the file",
    });
    expect(`o_field_widget span`).toHaveCount(0, {
        message:
            "the binary field should not display a filename in the link since we removed the file",
    });
});

test("BinaryField is correctly rendered (isDirty)", async () => {
    await mountView({
        resModel: "res.partner",
        resId: 1,
        type: "form",
        arch: `
            <form>
                <field name="document" filename="foo"/>
                <field name="foo"/>
            </form>
        `,
    });

    // Simulate a file upload
    await click(`.o_select_file_button`);
    await animationFrame();
    const file = new File(["test"], "fake_file.txt", { type: "text/plain" });
    await setInputFiles([file]);
    await waitFor(`.o_form_button_save:visible`);
    expect(`.o_field_widget[name="document"] .fa-download`).toHaveCount(0, {
        message:
            "the binary field should not be rendered as a downloadable since the record is dirty",
    });

    await clickSave();
    expect(`.o_field_widget[name="document"] .fa-download`).toHaveCount(1, {
        message:
            "the binary field should render as a downloadable link since the record is not dirty",
    });
});

test("file name field is not defined", async () => {
    await mountView({
        resModel: "res.partner",
        resId: 1,
        type: "form",
        arch: `<form><field name="document" filename="foo"/></form>`,
    });
    expect(`.o_field_binary`).toHaveText("", {
        message: "there should be no text since the name field is not in the view",
    });
    expect(`.o_field_binary .fa-download`).toBeDisplayed({
        message: "download icon should be visible",
    });
});

test("icons are displayed exactly once", async () => {
    await mountView({
        resModel: "res.partner",
        resId: 1,
        type: "form",
        arch: `<form><field name="document" filename="foo"/></form>`,
    });
    expect(queryOne`.o_field_binary .o_select_file_button`).toBeVisible({
        message: "only one select file icon should be visible",
    });
    expect(queryOne`.o_field_binary .o_download_file_button`).toBeVisible({
        message: "only one download file icon should be visible",
    });
    expect(queryOne`.o_field_binary .o_clear_file_button`).toBeVisible({
        message: "only one clear file icon should be visible",
    });
});

test("input value is empty when clearing after uploading", async () => {
    await mountView({
        resModel: "res.partner",
        resId: 1,
        type: "form",
        arch: `
            <form>
                <field name="document" filename="foo"/>
                <field name="foo"/>
            </form>
        `,
    });

    await click(`.o_select_file_button`);
    await animationFrame();
    const file = new File(["test"], "fake_file.txt", { type: "text/plain" });
    await setInputFiles([file]);
    await waitFor(`.o_form_button_save:visible`);
    expect(`.o_field_binary input[type=text]`).toHaveAttribute("readonly");
    expect(`.o_field_binary input[type=text]`).toHaveValue("fake_file.txt");
    expect(`.o_field_char input[type=text]`).toHaveValue("fake_file.txt");

    await click(`.o_clear_file_button`);
    await animationFrame();
    expect(`.o_field_binary .o_input_file`).toHaveValue("");
    expect(`.o_field_char input`).toHaveValue("");
});

test("option accepted_file_extensions", async () => {
    await mountView({
        resModel: "res.partner",
        type: "form",
        arch: `
            <form>
                <field name="document" widget="binary" options="{'accepted_file_extensions': '.dat,.bin'}"/>
            </form>
        `,
    });
    expect(`input.o_input_file`).toHaveAttribute("accept", ".dat,.bin", {
        message: "the input should have the correct ``accept`` attribute",
    });
});

test.tags("desktop");
test("readonly in create mode does not download", async () => {
    onRpc("/web/content", () => {
        expect.step("We shouldn't be getting the file.");
    });

    Partner._onChanges.product_id = (record) => {
        record.document = "onchange==\n";
    };
    Partner._fields.document.readonly = true;

    await mountView({
        resModel: "res.partner",
        type: "form",
        arch: `
            <form>
                <field name="product_id"/>
                <field name="document" filename="yooo"/>
            </form>
        `,
    });

    await click(`.o_field_many2one[name='product_id'] input`);
    await animationFrame();
    await click(`.o_field_many2one[name='product_id'] .dropdown-item`);
    await animationFrame();
    expect(`.o_field_widget[name="document"] a`).toHaveCount(0, {
        message: "The link to download the binary should not be present",
    });
    expect(`.o_field_widget[name="document"] a > .fa-download`).toHaveCount(0, {
        message: "The download icon should not be present",
    });
    expect.verifySteps([]);
});

test("BinaryField in list view (formatter)", async () => {
    Partner._records[0]["document"] = BINARY_FILE;
    await mountView({
        resModel: "res.partner",
        type: "list",
        arch: `<list><field name="document"/></list>`,
    });
    expect(`.o_data_row .o_data_cell`).toHaveText("93.43 Bytes");
});

test("BinaryField in list view with filename", async () => {
    Partner._records[0]["document"] = BINARY_FILE;
    await mountView({
        resModel: "res.partner",
        type: "list",
        arch: `
            <list>
                <field name="document" filename="foo" widget="binary"/>
                <field name="foo"/>
            </list>
        `,
    });
    expect(`.o_data_row .o_data_cell`).toHaveText("coucou.txt");
});

test("new record has no download button", async () => {
    Partner._fields.document.default = BINARY_FILE;
    await mountView({
        resModel: "res.partner",
        type: "form",
        arch: `<form><field name="document" filename="foo"/></form>`,
    });
    expect(`button.fa-download`).toHaveCount(0);
});

test("filename doesn't exceed 255 bytes", async () => {
    const LARGE_BINARY_FILE = BINARY_FILE.repeat(5);
    expect((LARGE_BINARY_FILE.length / 4) * 3).toBeGreaterThan(MAX_FILENAME_SIZE_BYTES, {
        message:
            "The initial binary file should be larger than max bytes that can represent the filename",
    });

    Partner._fields.document.default = LARGE_BINARY_FILE;
    await mountView({
        resModel: "res.partner",
        type: "form",
        arch: `<form><field name="document"/></form>`,
    });
    expect(queryValue(`.o_field_binary input[type=text]`)).toHaveLength(
        toBase64Length(MAX_FILENAME_SIZE_BYTES),
        {
            message: "The filename shouldn't exceed the maximum size in bytes in base64",
        }
    );
});

test("filename is updated when using the pager", async () => {
    Partner._records.push(
        { id: 1, document: "abc", foo: "abc.txt" },
        { id: 2, document: "def", foo: "def.txt" }
    );
    await mountView({
        resModel: "res.partner",
        resIds: [1, 2],
        resId: 1,
        type: "form",
        arch: `
            <form>
                <field name="document" filename="foo"/>
                <field name="foo"/>
            </form>
        `,
    });
    expect(`.o_field_binary input[type=text]`).toHaveValue("abc.txt", {
        message: `displayed value should be "abc.txt"`,
    });

    await pagerNext();
    expect(`.o_field_binary input[type=text]`).toHaveValue("def.txt", {
        message: `displayed value should be "def.txt"`,
    });
});

test("isUploading state should be set to false after upload", async () => {
    expect.errors(1);

    Partner._records.push({ id: 1 });
    Partner._onChanges.document = (record) => {
        if (record.document) {
            throw makeServerError({ type: "ValidationError" });
        }
    };
    await mountView({
        resModel: "res.partner",
        resId: 1,
        type: "form",
        arch: `<form><field name="document"/></form>`,
    });

    await click(`.o_select_file_button`);
    await animationFrame();
    const file = new File(["test"], "fake_file.txt", { type: "text/plain" });
    await setInputFiles([file]);
    await waitFor(`.o_form_button_save:visible`);
    await animationFrame();
    expect.verifyErrors([/RPC_ERROR/]);
    expect(`.o_select_file_button`).toHaveText("Upload your file");
});

test("doesn't crash if value is not a string", async () => {
    class Dummy extends models.Model {
        document = fields.Binary();
        _applyComputesAndValidate() {}
    }
    defineModels([Dummy]);
    Dummy._records.push({ id: 1, document: {} });
    await mountView({
        type: "form",
        resModel: "dummy",
        resId: 1,
        arch: `
            <form>
                <field name="document"/>
            </form>`,
    });
    expect(".o_field_binary input").toHaveValue("");
});
