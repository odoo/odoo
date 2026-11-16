import { BinaryFileManager } from "@base_import/binary_file_manager";
import { BaseImportModel } from "@base_import/import_model";
import { expect, test } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

test("local images follow the row IDs of their owning model", async () => {
    patchWithCleanup(BinaryFileManager.prototype, {
        async _readFile(file) {
            return `data:image/png;base64,${file.data}`;
        },
    });
    const model = Object.assign(Object.create(BaseImportModel.prototype), {
        resModel: "product.template",
        context: {},
        importOptionsValues: {
            tracking_disable: { value: true },
            date_format: { value: "YYYY-MM-DD" },
            datetime_format: { value: "YYYY-MM-DD HH:mm:SS" },
        },
        fieldsToHandle: {},
        binaryFilesParams: {
            binaryFiles: {
                value: {
                    "main.png": { data: "bWFpbg==" },
                    "first.png": { data: "Zmlyc3Q=" },
                    "second.png": { data: "c2Vjb25k" },
                    "third.png": { data: "dGhpcmQ=" },
                },
            },
            maxSizePerBatch: { value: 10 },
            delayAfterEachBatch: { value: 0 },
        },
        orm: {
            async call(resModel, method, args, kwargs) {
                expect(method).toBe("load");
                expect(kwargs.fields).toEqual([".id", "image_1920"]);
                expect.step([resModel, kwargs.data]);
                return { ids: [], messages: [] };
            },
        },
    });
    const ids = [42, false, 43];
    const filenames = {
        image_1920: ["main.png", null, null],
        "product_template_image_ids/image_1920": ["first.png", "second.png", "third.png"],
    };
    const recordIds = {
        "": { model: "product.template", ids },
        product_template_image_ids: { model: "product.image", ids: [7, 8, 9] },
    };
    await model._pushLocalImageToRecords(recordIds, filenames, true);
    await model._pushLocalImageToRecords(undefined, filenames, false);
    expect.verifySteps([]);

    model._callImport = async () => ({
        ids: [42, 43],
        record_ids: recordIds,
        binary_filenames: filenames,
    });
    const importResult = { ids: [], fields: [], columns: [] };
    await model._executeImportStep(false, importResult);
    expect(importResult.ids).toEqual([42, 43]);
    expect.verifySteps([
        ["product.template", [[42, "bWFpbg=="]]],
        [
            "product.image",
            [
                [7, "Zmlyc3Q="],
                [8, "c2Vjb25k"],
                [9, "dGhpcmQ="],
            ],
        ],
    ]);
});
