// @ts-check

import { expect, test } from "@odoo/hoot";
import { FileModel } from "@web/components/file_viewer/file_model";

test("isUrlYoutube returns false when url is a boolean false (binary attachment)", () => {
    // ir.attachment.url is False in Python for binary files → false in JS
    const fileModel = Object.assign(new FileModel(), { url: false, type: "binary" });
    expect(fileModel.isUrlYoutube).toBe(false);
});

test("isUrlYoutube returns false when url is null or undefined", () => {
    const fileModel = new FileModel();
    expect(fileModel.isUrlYoutube).toBe(false);

    const fileModelNull = Object.assign(new FileModel(), { url: null });
    expect(fileModelNull.isUrlYoutube).toBe(false);
});

test("isUrlYoutube returns true for YouTube URLs", () => {
    const fileModel = Object.assign(new FileModel(), {
        url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        type: "url",
    });
    expect(fileModel.isUrlYoutube).toBe(true);

    const fileModelShort = Object.assign(new FileModel(), {
        url: "https://youtu.be/dQw4w9WgXcQ",
        type: "url",
    });
    expect(fileModelShort.isUrlYoutube).toBe(true);
});

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
