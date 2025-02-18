import { expect, test } from "@odoo/hoot";
import { FileModel } from "@web/core/file_viewer/file_model";

test("returns correct URL for files with ID", async () => {
    const imageFile = new FileModel();
    Object.assign(imageFile, {
        id: 123,
        mimetype: "image/png",
        name: "test.png",
    });

    const regularFile = new FileModel();
    Object.assign(regularFile, {
        id: 456,
        mimetype: "application/pdf",
        name: "test.pdf",
    });

    expect(imageFile.urlRoute).toBe("/web/image/123");
    expect(regularFile.urlRoute).toBe("/web/content/456");
});

test("returns direct URL for files without ID", async () => {
    const fileWithoutId = new FileModel();
    const directUrl = "https://example.com/file.pdf";
    Object.assign(fileWithoutId, {
        id: undefined,
        url: directUrl,
        mimetype: "application/pdf",
        name: "file.pdf",
    });

    expect(fileWithoutId.urlRoute).toBe(directUrl);
});

test("prioritizes ID over direct URL when both are present", async () => {
    const imageFile = new FileModel();
    Object.assign(imageFile, {
        id: 789,
        url: "https://example.com/direct-image.jpg",
        mimetype: "image/jpeg",
        name: "image.jpg",
    });

    const regularFile = new FileModel();
    Object.assign(regularFile, {
        id: 101,
        url: "https://example.com/direct-file.pdf",
        mimetype: "application/pdf",
        name: "document.pdf",
    });

    expect(imageFile.urlRoute).toBe("/web/image/789");
    expect(regularFile.urlRoute).toBe("/web/content/101");
});
