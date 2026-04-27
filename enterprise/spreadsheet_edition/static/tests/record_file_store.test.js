import { mockService } from "@web/../tests/web_test_helpers";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { describe, expect, test } from "@odoo/hoot";
import { RecordFileStore } from "@spreadsheet_edition/bundle/image/record_file_store";
import { makeSpreadsheetMockEnv } from "@spreadsheet/../tests/helpers/model";

describe.current.tags("headless");
defineSpreadsheetModels();

test("upload image", async () => {
    const fakeHTTPService = {
        post: (route, params) => {
            expect.step("image uploaded");
            expect(params.model).toBe("res.partner");
            expect(params.id).toBe(1);
            expect(route).toBe("/web/binary/upload_attachment");
            return JSON.stringify([
                {
                    id: 10,
                    name: params.ufile[0].name,
                    mimetype: "image/png",
                },
            ]);
        },
    };
    const fakeORMService = {
        call: (model, method, args) => {
            expect.step("access token generated");
            expect(model).toBe("ir.attachment");
            expect(method).toBe("generate_access_token");
            expect(args).toEqual([10]);
            return ["the-image-access-token"];
        },
    };
    mockService("http", fakeHTTPService);
    mockService("orm", fakeORMService);
    const env = await makeSpreadsheetMockEnv();
    const fileStore = new RecordFileStore("res.partner", 1, env.services.http, env.services.orm);
    const path = await fileStore.upload(new File(["image"], "image_name.png", { type: "image/png" }));
    expect(path).toBe("/web/image/10?access_token=the-image-access-token");
    expect.verifySteps(["image uploaded", "access token generated"]);
});

test("delete image", async () => {
    const env = await makeSpreadsheetMockEnv({
        mockRPC: (route, args) => {
            if (args.method === "unlink") {
                const ids = args.args[0];
                expect.step(`image ${ids} deleted`);
                expect(args.model).toBe("ir.attachment");
                return true;
            }
        },
    });
    const fileStore = new RecordFileStore("res.partner", 1, env.services.http, env.services.orm);
    await fileStore.delete("/web/image/10");
    await fileStore.delete("/web/image/11?access_token=the-image-access-token");
    expect.verifySteps(["image 10 deleted", "image 11 deleted"]);
});

test("delete file with path without attachment id", async () => {
    const env = await makeSpreadsheetMockEnv({
        mockRPC: (route, args) => {
            if (args.method === "unlink") {
                throw new Error("unlink should not be called");
            }
        },
    });
    const fileStore = new RecordFileStore("res.partner", 1, env.services.http, env.services.orm);
    await expect(fileStore.delete("/web/image/path/without/id")).rejects.toThrow();
});
