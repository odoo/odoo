/* global QRCode */

import { session } from "@web/session";
import { getDataURLFromFile } from "@web/core/utils/urls";
import { deserializeDateTime } from "@web/core/l10n/dates";
/*
 * comes from o_spreadsheet.js
 * https://stackoverflow.com/questions/105034/create-guid-uuid-in-javascript
 * */
export function uuidv4() {
    // mainly for jest and other browsers that do not have the crypto functionality
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
        const r = (Math.random() * 16) | 0,
            v = c == "x" ? r : (r & 0x3) | 0x8;
        return v.toString(16);
    });
}

/**
 * Formats the given `url` with correct protocol and port.
 * Useful for communicating to local iot box instance.
 * @param {string} url
 * @returns {string}
 */
export function deduceUrl(url) {
    const protocol = odoo.use_lna ? "http:" : window.location.protocol;
    if (!url.includes("//")) {
        url = `${protocol}//${url}`;
    }
    if (url.indexOf(":", 6) < 0) {
        url += ":" + (protocol === "https:" ? 443 : 8069);
    }
    return url;
}

export function constructAttributeString(line) {
    let attributeString = "";

    if (line.attribute_value_ids && line.attribute_value_ids.length > 0) {
        for (const value of line.attribute_value_ids) {
            if (value.is_custom) {
                const customValue = line.custom_attribute_value_ids.find(
                    (cus) =>
                        cus.custom_product_template_attribute_value_id?.id == parseInt(value.id)
                );
                if (customValue) {
                    attributeString += `${value.attribute_id.name}: ${value.name}: ${customValue.custom_value}, `;
                }
            } else {
                attributeString += `${value.name}, `;
            }
        }

        attributeString = attributeString.slice(0, -2);
    } else if (
        attributeString === "" &&
        line?.product_id?.product_template_variant_value_ids?.length > 0
    ) {
        attributeString = line.product_id.product_template_variant_value_ids
            ?.map((attr) => attr.name)
            .join(", ");
    }

    return attributeString;
}

export function constructFullProductName(line) {
    const attributeString = constructAttributeString(line);
    return attributeString
        ? `${line?.product_id?.name} (${attributeString})`
        : `${line?.product_id?.name}`;
}
/**
 * Returns a random 5 digits alphanumeric code
 * @returns {string}
 */
export function random5Chars() {
    let code = "";
    while (code.length != 5) {
        code = Math.random().toString(36).slice(2, 7);
    }
    return code;
}

export function qrCodeSrc(url, { size = 200 } = {}) {
    return `/report/barcode/QR/${encodeURIComponent(url)}?width=${size}&height=${size}`;
}

/**
 * @template T
 * @param {T[]} entries - The array of objects to search through.
 * @param {Function} [criterion=(x) => x] - A function that returns a number for each entry. The entry with the highest value of this function will be returned. If not provided, defaults to an identity function that returns the entry itself.
 * @param {boolean} [inverted=false] - If true, the entry with the lowest value of the criterion function will be returned instead.
 * @returns {T} The entry with the highest or lowest value of the criterion function, depending on the value of `inverted`.
 */
export function getMax(entries, { criterion = (x) => x, inverted = false } = {}) {
    return entries.reduce((prev, current) => {
        const res = criterion(prev) > criterion(current);
        return (inverted ? !res : res) ? prev : current;
    });
}
export function getMin(entries, options) {
    return getMax(entries, { ...options, inverted: true });
}
export function getOnNotified(bus, channel) {
    bus.addChannel(channel);
    return (notif, callback) => bus.subscribe(`${channel}-${notif}`, callback);
}

/**
 * Loading image is converted to a Promise to allow await when
 * loading an image. It resolves to the loaded image if successful,
 * else, resolves to false.
 *
 * [Source](https://stackoverflow.com/questions/45788934/how-to-turn-this-callback-into-a-promise-using-async-await)
 */
export function loadImage(url, options = {}) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.addEventListener("load", () => resolve(img));
        img.addEventListener("error", () => {
            if (options.onError) {
                options.onError();
            }
            reject(new Error(`Failed to load image at ${url}`));
        });
        img.src = url;
    });
}

/**
 * Load all images in the given element.
 * @param {HTMLElement} el
 */

export function waitImages(containerElement, timeoutMs = 3000) {
    return new Promise((resolve) => {
        const images = containerElement.querySelectorAll("img");
        const total = images.length;
        let loadedCount = 0;
        let timedOut = false;

        if (total === 0) {
            resolve({ timedOut: false });
            return;
        }

        const timeoutId = setTimeout(() => {
            timedOut = true;
            resolve({ timedOut: true });
        }, timeoutMs);

        const onLoadOrError = () => {
            loadedCount++;
            if (loadedCount === total && !timedOut) {
                clearTimeout(timeoutId);
                resolve({ timedOut: false });
            }
        };

        images.forEach((img) => {
            if (img.complete) {
                onLoadOrError();
            } else {
                img.addEventListener("load", onLoadOrError);
                img.addEventListener("error", onLoadOrError);
            }
        });
    });
}

export class Counter {
    constructor(start = 0) {
        this.value = start;
    }
    next() {
        this.value++;
        return this.value;
    }
}

export function isValidEmail(email) {
    return email && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export const LONG_PRESS_DURATION = session.test_mode ? 100 : 500;

export async function getImageDataUrl(imageUrl) {
    const res = await fetch(imageUrl);
    const blob = await res.blob();
    return await getDataURLFromFile(blob);
}

export function orderUsageUTCtoLocalUtil(data) {
    const result = {};
    for (const [datetime, usage] of Object.entries(data)) {
        const dt = deserializeDateTime(datetime);
        const formattedDt = dt.toFormat("yyyy-MM-dd HH:mm:ss");
        result[formattedDt] = usage;
    }
    return result;
}

/**
 * Generates a QR code as a data URL in SVG format for a given URL.
 *
 * @param {string} url - The URL or text to encode in the QR code.
 * @param {Object} [options={}] - Optional configuration for the QR code.
 * @param {number} [options.width=150] - The width of the QR code.
 * @param {number} [options.height=150] - The height of the QR code.
 * @param {number} [options.correctLevel=QRCode.CorrectLevel.L] - The error correction level for the QR code.
 * @param {boolean} [options.useSVG=true] - Whether to generate the QR code as SVG.
 * @param {Object} [options.rest] - Additional options to pass to the QRCode constructor.
 * @returns {string} The QR code as a data URL in SVG format.
 */
export function generateQRCodeDataUrl(
    url,
    { width = 150, height = 150, correctLevel = QRCode.CorrectLevel.L, ...rest } = {}
) {
    const tempDiv = document.createElement("div");
    const options = { width, height, correctLevel, ...rest };

    new QRCode(tempDiv, { text: url, useSVG: true, ...options });

    const svg = tempDiv.querySelector("svg");
    svg.setAttribute("width", width);
    svg.setAttribute("height", height);

    const qr_code_svg = new XMLSerializer().serializeToString(svg);
    return "data:image/svg+xml;base64," + window.btoa(qr_code_svg);
}
