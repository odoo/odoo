/**
 * In order to avoid as many RPC calls as possible with image data, every time
 * an image has to be converted because it is not compatible with mail clients
 * as is, a checksum representing the image parameters is generated
 * (data-email-image-src | data-email-image-checksum). Past checksums are
 * cached per user session, and only the last checksum is stored in body_arch.
 */
const VERSION = "1";
const PRECISION = 1e-1;

function normalizeNumber(value, scale = 1) {
    return Math.round((scale * (value || 0)) / PRECISION) * PRECISION;
}

export function normalizeDimensions(dimensions, scale = 1) {
    return {
        height: normalizeNumber(dimensions.height, scale),
        width: normalizeNumber(dimensions.width, scale),
    };
}

export function normalizePosition(position, scale = 1) {
    return {
        x: normalizeNumber(position.x, scale),
        y: normalizeNumber(position.y, scale),
    };
}

function generateEmailBackgroundJSON(
    src,
    mimetype,
    renderedDimensions,
    targetDimensions,
    targetPosition,
    filterData
) {
    return JSON.stringify({
        filterData,
        mimetype: mimetype?.toLowerCase(),
        renderedDimensions,
        src,
        targetDimensions,
        targetPosition,
        type: "background",
        version: VERSION,
    });
}

function generateEmailImgJSON(src, mimetype, renderedDimensions) {
    return JSON.stringify({
        mimetype: mimetype?.toLowerCase(),
        renderedDimensions,
        src,
        type: "img",
        version: VERSION,
    });
}

export async function computeEmailImageChecksum(
    nodeType,
    src,
    mimetype,
    renderedDimensions,
    targetDimensions,
    targetPosition,
    filterData
) {
    let json;
    if (nodeType.toUpperCase() === "IMG") {
        json = generateEmailImgJSON(src, mimetype, renderedDimensions);
    } else {
        json = generateEmailBackgroundJSON(
            src,
            mimetype,
            renderedDimensions,
            targetDimensions,
            targetPosition,
            filterData
        );
    }
    const encoder = new TextEncoder();
    const data = encoder.encode(json);
    const hashBuffer = await crypto.subtle.digest("SHA-256", data);
    return [...new Uint8Array(hashBuffer)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
