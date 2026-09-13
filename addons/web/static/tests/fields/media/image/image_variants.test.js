// @ts-check

import { afterEach, beforeEach, expect, test } from "@odoo/hoot";
import { enableLogging, getStatus, makeLogger } from "@web/core/debug/debug_logger";
import {
    convertUploadToWebp,
    createWebpVariantAttachments,
    ImageDecodeError,
} from "@web/fields/media/image/image_variants";

const log = makeLogger("web.field.image_variants");
let previousLogSpec;
beforeEach(() => {
    previousLogSpec = getStatus().spec;
    enableLogging("web.field.image_variants", { persist: false });
});
afterEach(() => enableLogging(previousLogSpec, { persist: false }));

const PNG_5X5 =
    "iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==";

function makeOrmSpy(idsByCall = [[1], [2, 3, 4], true]) {
    const calls = [];
    let index = 0;
    return {
        calls,
        call(model, method, args) {
            calls.push({ model, method, records: args[0] });
            return Promise.resolve(idsByCall[index++]);
        },
    };
}

test("convertUploadToWebp leaves non-convertible types untouched", async () => {
    for (const type of ["image/gif", "image/svg+xml", "image/webp"]) {
        const info = { data: PNG_5X5, type, name: `x${type}` };
        expect(await convertUploadToWebp(info)).toBe(info, {
            message: `${type} must be returned as-is, same object`,
        });
    }
});

test("convertUploadToWebp re-encodes a png and renames it", async () => {
    const result = await convertUploadToWebp({
        data: PNG_5X5,
        type: "image/png",
        name: "photo.png",
    });
    if (result.type === "image/webp") {
        expect(result.name).toBe("photo.webp");
        expect(result.data).not.toBe(PNG_5X5);
    } else {
        expect(result.type).toBe("image/png");
        expect(result.name).toBe("photo.png");
        expect(result.data).toBe(PNG_5X5);
    }
});

test("convertUploadToWebp raises ImageDecodeError on undecodable bytes", async () => {
    let caught = null;
    try {
        await convertUploadToWebp({
            data: "bm90LWFuLWltYWdl",
            type: "image/png",
            name: "broken.png",
        });
    } catch (error) {
        caught = error;
    }
    expect(caught).toBeInstanceOf(ImageDecodeError);
});

test("createWebpVariantAttachments raises ImageDecodeError on undecodable bytes", async () => {
    const orm = makeOrmSpy();
    let caught = null;
    try {
        await createWebpVariantAttachments(orm, {
            data: "bm90LWFuLWltYWdl",
            name: "broken.webp",
        });
    } catch (error) {
        caught = error;
    }
    expect(caught).toBeInstanceOf(ImageDecodeError);
    expect(orm.calls).toHaveLength(0, {
        message: "nothing must be persisted when the source cannot be decoded",
    });
});

test("createWebpVariantAttachments stores the original verbatim and a jpeg fallback", async () => {
    const orm = makeOrmSpy();
    await createWebpVariantAttachments(orm, { data: PNG_5X5, name: "photo.webp" });

    expect(orm.calls).toHaveLength(2);

    const [original] = orm.calls[0].records;
    expect(orm.calls[0].method).toBe("create_unique");
    expect(original.mimetype).toBe("image/webp");
    expect(original.datas).toBe(PNG_5X5, {
        message: "the original keeps the uploaded bytes, never a re-drawn copy",
    });
    expect(original.res_id).toBe(undefined);

    const jpegs = orm.calls[1].records;
    expect(jpegs).toHaveLength(1);
    expect(jpegs[0].mimetype).toBe("image/jpeg");
    expect(jpegs[0].name).toBe("photo.jpg");
    expect(jpegs[0].description).toBe("format: jpeg");
    expect(jpegs[0].res_id).toBe(1, {
        message: "the fallback hangs off the webp of its own size",
    });
});

for (const [width, height] of [
    [4000, 1],
    [1, 4000],
    [1, 1],
    [4000, 2000],
]) {
    test(`image variants remain decodable for ${width}x${height}`, async () => {
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const data = canvas.toDataURL("image/webp").split(",")[1];
        const orm = makeOrmSpy([[1], [2, 3, 4, 5, 6], []]);
        await createWebpVariantAttachments(orm, { data, name: "image.webp" });
        for (const { records } of orm.calls) {
            for (const record of records) {
                expect(Boolean(record.datas)).toBe(true);
                const image = document.createElement("img");
                image.src = `data:${record.mimetype};base64,${record.datas}`;
                await image.decode();
                log.logic("decoded variant", {
                    width: image.naturalWidth,
                    height: image.naturalHeight,
                    mimetype: record.mimetype,
                });
                expect(image.naturalWidth).toBeGreaterThan(0);
                expect(image.naturalHeight).toBeGreaterThan(0);
            }
        }
    });
}
