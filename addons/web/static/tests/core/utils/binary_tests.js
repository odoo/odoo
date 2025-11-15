/** @odoo-module **/

import { humanSize } from "@web/core/utils/binary";
import { resizeBlobImg } from "@web/core/utils/files";

QUnit.module("utils", () => {
    QUnit.module("binary");

    QUnit.test("humanSize", (assert) => {
        assert.strictEqual(humanSize(0), "0.00 Bytes");
        assert.strictEqual(humanSize(3), "3.00 Bytes");
        assert.strictEqual(humanSize(2048), "2.00 Kb");
        assert.strictEqual(humanSize(2645000), "2.52 Mb");
    });

    QUnit.test("resize image", async (assert) => {
        function buildblobImage(w, h) {
            return new Promise((resolve) => {
                const canvas = document.createElement("canvas");
                canvas.width = w;
                canvas.height = h;
                const ctx = canvas.getContext("2d");
                ctx.fillStyle = "rgb(200 0 0)";
                ctx.fillRect(0, 0, w / 2, h / 2);
                canvas.toBlob(resolve);
            });
        }

        function blobTob64(blob) {
            return new Promise((resolve) => {
                const reader = new FileReader();
                reader.readAsDataURL(blob);
                reader.onloadend = () => {
                    resolve(reader.result);
                };
            });
        }

        const bigBlobImg = await buildblobImage(256, 256);
        const smallBlobImg = await buildblobImage(64, 64);

        const resized = await resizeBlobImg(bigBlobImg, { width: 64, height: 64 });
        const smallBlobImgB64 = await blobTob64(smallBlobImg);
        assert.ok(smallBlobImgB64);
        assert.strictEqual(await blobTob64(resized), smallBlobImgB64);
    });
});
