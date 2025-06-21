/** @odoo-module **/

import { FileModel } from "@web/core/file_viewer/file_model";

QUnit.module("FileModel", () => {
    QUnit.module("URL Routing", () => {
        QUnit.test("returns correct URL for files with ID", (assert) => {
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

            assert.strictEqual(
                imageFile.urlRoute,
                "/web/image/123",
                "Should return correct image URL route with ID"
            );

            assert.strictEqual(
                regularFile.urlRoute,
                "/web/content/456",
                "Should return correct content URL route with ID"
            );
        });

        QUnit.test("returns direct URL for files without ID", (assert) => {
            const fileWithoutId = new FileModel();
            const directUrl = "https://example.com/file.pdf";
            Object.assign(fileWithoutId, {
                id: undefined,
                url: directUrl,
                mimetype: "application/pdf",
                name: "file.pdf",
            });

            assert.strictEqual(
                fileWithoutId.urlRoute,
                directUrl,
                "Should return direct URL when ID is not present"
            );
        });

        QUnit.test("prioritizes ID over direct URL when both are present", (assert) => {
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

            assert.strictEqual(
                imageFile.urlRoute,
                "/web/image/789",
                "Should use ID-based route for image even when direct URL is present"
            );

            assert.strictEqual(
                regularFile.urlRoute,
                "/web/content/101",
                "Should use ID-based route for regular file even when direct URL is present"
            );
        });
    });
});
