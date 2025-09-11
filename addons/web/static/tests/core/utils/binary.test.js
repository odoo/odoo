import { describe, expect, test } from "@odoo/hoot";
import { patchTranslations } from "@web/../tests/web_test_helpers";

import { humanSize } from "@web/core/utils/binary";
import { resizeBlobImg } from "@web/core/utils/files";

describe.current.tags("headless");

test("humanSize", () => {
    patchTranslations();
    expect(humanSize(0)).toBe("0.00 Bytes");
    expect(humanSize(3)).toBe("3.00 Bytes");
    expect(humanSize(2048)).toBe("2.00 Kb");
    expect(humanSize(2645000)).toBe("2.52 Mb");
});

test("resize image", async () => {
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
    expect(smallBlobImgB64).not.toBeEmpty();
    expect(await blobTob64(resized)).toBe(smallBlobImgB64);
});
