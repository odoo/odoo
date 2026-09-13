// @ts-check
/** @odoo-module native */

const VARIANT_SIZES = [1920, 1024, 512, 256, 128];

const NON_CONVERTIBLE_TYPES = ["image/gif", "image/svg+xml", "image/webp"];

export class ImageDecodeError extends Error {}

/**
 * @param {string} src
 * @returns {Promise<HTMLImageElement>}
 */
async function decodeImage(src) {
    const image = document.createElement("img");
    image.src = src;
    try {
        await image.decode();
    } catch (error) {
        throw new ImageDecodeError("the uploaded image could not be decoded", {
            cause: error,
        });
    }
    return image;
}

/** @returns {boolean} */
function canEncodeWebp() {
    return document
        .createElement("canvas")
        .toDataURL("image/webp")
        .startsWith("data:image/webp");
}

/**
 * @param {HTMLImageElement} image
 * @returns {HTMLCanvasElement}
 */
function drawFullSize(image) {
    const canvas = document.createElement("canvas");
    canvas.width = image.width;
    canvas.height = image.height;
    /** @type {any} */ (canvas.getContext("2d")).drawImage(image, 0, 0);
    return canvas;
}

/**
 * @param {HTMLImageElement} image
 * @param {number} ratio
 * @returns {HTMLCanvasElement}
 */
function drawScaled(image, ratio) {
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(image.width * ratio));
    canvas.height = Math.max(1, Math.round(image.height * ratio));
    const ctx = /** @type {any} */ (canvas.getContext("2d"));
    ctx.fillStyle = "transparent";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(
        image,
        0,
        0,
        image.width,
        image.height,
        0,
        0,
        canvas.width,
        canvas.height,
    );
    return canvas;
}

/**
 * @param {{ data: string, type: string, name: string }} info
 * @returns {Promise<{ data: string, type: string, name: string }>}
 * @throws {ImageDecodeError}
 */
export async function convertUploadToWebp(info) {
    if (NON_CONVERTIBLE_TYPES.includes(info.type)) {
        return info;
    }
    const image = await decodeImage(`data:${info.type};base64,${info.data}`);
    const dataURL = drawFullSize(image).toDataURL("image/webp");
    if (!dataURL.startsWith("data:image/webp")) {
        return info;
    }
    return {
        ...info,
        data: dataURL.split(",")[1],
        type: "image/webp",
        name: info.name.replace(/\.[^/.]+$/, ".webp"),
    };
}

/**
 * @param {{ call: (model: string, method: string, args: any[]) => Promise<any> }} orm
 * @param {{ data: string, name: string }} info
 * @throws {ImageDecodeError}
 */
export async function createWebpVariantAttachments(orm, info) {
    const image = await decodeImage(`data:image/webp;base64,${info.data}`);
    const originalSize = Math.max(image.width, image.height);
    const smallerSizes = canEncodeWebp()
        ? VARIANT_SIZES.filter((size) => size < originalSize)
        : [];
    const variants = [originalSize, ...smallerSizes].map((size) => ({
        size,
        canvas: drawScaled(image, size / originalSize),
    }));

    const [originalId] = await orm.call("ir.attachment", "create_unique", [
        [
            {
                name: info.name,
                description: "",
                datas: info.data,
                res_model: "ir.attachment",
                mimetype: "image/webp",
            },
        ],
    ]);

    const resizedVariants = variants.filter(({ size }) => size !== originalSize);
    const resizedIds = resizedVariants.length
        ? await orm.call("ir.attachment", "create_unique", [
              resizedVariants.map(({ size, canvas }) => ({
                  name: info.name,
                  description: `resize: ${size}`,
                  datas: canvas.toDataURL("image/webp").split(",")[1],
                  res_id: originalId,
                  res_model: "ir.attachment",
                  mimetype: "image/webp",
              })),
          ])
        : [];

    const idBySize = new Map(
        /** @type {[number, number][]} */ ([
            [originalSize, originalId],
            ...resizedVariants.map(({ size }, index) => [size, resizedIds[index]]),
        ]),
    );
    await orm.call("ir.attachment", "create_unique", [
        variants.map(({ size, canvas }) => ({
            name: info.name.replace(/\.webp$/, ".jpg"),
            description: "format: jpeg",
            datas: canvas.toDataURL("image/jpeg").split(",")[1],
            res_id: idBySize.get(size),
            res_model: "ir.attachment",
            mimetype: "image/jpeg",
        })),
    ]);
}
