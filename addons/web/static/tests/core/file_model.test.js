import { expect, test } from "@odoo/hoot";

import { FileModel } from "@web/core/file_viewer/file_model";

test("url query params of FileModel returns proper params", () => {
    const attachmentData = {
        access_token: "4b52e31e-a155-4598-8d15-538f64f0fb7b",
        checksum: "f6a9d2bcbb34ce90a73785d8c8d1b82e5cdf0b5b",
        extension: "jpg",
        name: "test.jpg",
        mimetype: "image/jpeg",
    };
    const expectedQueryParams = {
        access_token: "4b52e31e-a155-4598-8d15-538f64f0fb7b",
        filename: "test.jpg",
        unique: "f6a9d2bcbb34ce90a73785d8c8d1b82e5cdf0b5b",
    };
    const fileModel = Object.assign(new FileModel(), attachmentData);
    expect(fileModel.urlQueryParams).toEqual(expectedQueryParams);
});
