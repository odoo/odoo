/** @odoo-module native */
/* global QRCode */

import { makeLogger } from "@web/core/debug/debug_logger";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { getDataURLFromFile } from "@web/core/utils/urls";
import { session } from "@web/session";
const imageLog = makeLogger("pos.images");
export function uuidv4() {
    if (typeof crypto !== "undefined") {
        if (typeof crypto.randomUUID === "function") {
            return crypto.randomUUID();
        }
        if (typeof crypto.getRandomValues === "function") {
            const bytes = crypto.getRandomValues(new Uint8Array(16));
            bytes[6] = (bytes[6] & 0x0f) | 0x40;
            bytes[8] = (bytes[8] & 0x3f) | 0x80;
            const hex = [...bytes].map((b) => b.toString(16).padStart(2, "0"));
            return [
                hex.slice(0, 4).join(""),
                hex.slice(4, 6).join(""),
                hex.slice(6, 8).join(""),
                hex.slice(8, 10).join(""),
                hex.slice(10, 16).join(""),
            ].join("-");
        }
    }
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
        const r = (Math.random() * 16) | 0,
            v = c === "x" ? r : (r & 0x3) | 0x8;
        return v.toString(16);
    });
}

/**
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

export function getAttributeString(line) {
    let attributeString = "";

    if (line.attribute_value_ids && line.attribute_value_ids.length > 0) {
        for (const value of line.attribute_value_ids) {
            if (value.is_custom) {
                const customValue = line.custom_attribute_value_ids.find(
                    (cus) =>
                        cus.custom_product_template_attribute_value_id?.id ===
                        parseInt(value.id),
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

export function getFullProductName(line) {
    const attributeString = getAttributeString(line);
    return attributeString
        ? `${line?.product_id?.name} (${attributeString})`
        : `${line?.product_id?.name}`;
}
/**
 * @returns {string}
 */
export function random5Chars() {
    let code = "";
    while (code.length !== 5) {
        code = Math.random().toString(36).slice(2, 7);
    }
    return code;
}

export function getDeviceUuid() {
    if (!localStorage.getItem("device_uuid")) {
        localStorage.setItem("device_uuid", uuidv4());
    }
    return localStorage.getItem("device_uuid");
}

export function qrCodeSrc(url, { size = 200 } = {}) {
    return `/report/barcode/QR/${encodeURIComponent(url)}?width=${size}&height=${size}`;
}

/**
 * @template T
 * @param {T[]} entries
 * @param {Function} [criterion=(x) => x]
 * @param {boolean} [inverted=false]
 * @returns {T}
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
 * @param {HTMLElement} el
 */

export function waitImages(containerElement, timeoutMs = 3000) {
    return new Promise((resolve) => {
        const pending = new Set(
            [...containerElement.querySelectorAll("img")].filter(
                (img) => !img.complete,
            ),
        );
        if (!pending.size) {
            resolve({ timedOut: false });
            return;
        }
        const endWait = imageLog.perf("waitImages");
        const removeListeners = (img) => {
            img.removeEventListener("load", onLoadOrError);
            img.removeEventListener("error", onLoadOrError);
        };
        const finish = (timedOut) => {
            clearTimeout(timeoutId);
            for (const img of pending) {
                removeListeners(img);
            }
            endWait({ timedOut, pending: pending.size });
            pending.clear();
            resolve({ timedOut });
        };
        const onLoadOrError = ({ currentTarget: img }) => {
            removeListeners(img);
            pending.delete(img);
            if (!pending.size) {
                finish(false);
            }
        };
        const timeoutId = setTimeout(() => finish(true), timeoutMs);
        for (const img of pending) {
            img.addEventListener("load", onLoadOrError);
            img.addEventListener("error", onLoadOrError);
        }
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

export function isValidPhone(string) {
    const phone = string.replace(/[\s.\-()]/g, "");
    const pattern = /^\+\d{8,18}$/;
    return pattern.test(phone);
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
 * @param {string} url
 * @param {Object} [options={}]
 * @param {number} [options.width=150]
 * @param {number} [options.height=150]
 * @param {number} [options.correctLevel=QRCode.CorrectLevel.L]
 * @param {boolean} [options.useSVG=true]
 * @param {Object} [options.rest]
 * @returns {string}
 */
export function generateQRCodeDataUrl(
    url,
    { width = 150, height = 150, correctLevel = QRCode.CorrectLevel.L, ...rest } = {},
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
