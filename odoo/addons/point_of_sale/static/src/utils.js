/** @odoo-module */

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
    const { protocol } = window.location;
    if (!url.includes("//")) {
        url = `${protocol}//${url}`;
    }
    if (url.indexOf(":", 6) < 0) {
        url += ":" + (protocol === "https:" ? 443 : 8069);
    }
    return url;
}
export function constructFullProductName(line, attribute_value_by_id, display_name) {
    let attributeString = "";
    if (line.attribute_value_ids && line.attribute_value_ids.length > 0) {
        for (const valId of line.attribute_value_ids) {
            const value = attribute_value_by_id[valId];
            if (value.is_custom) {
                const customValue = line.custom_attribute_value_ids.find(
                    (cus) => cus.custom_product_template_attribute_value_id == parseInt(valId)
                );
                attributeString += customValue
                    ? `${value.name}: ${customValue.custom_value}, `
                    : `${value.name}, `;
            } else {
                attributeString += `${value.name}, `;
            }
        }
        attributeString = attributeString.slice(0, -2);
        attributeString = `(${attributeString})`;
    }

    return attributeString !== "" ? `${display_name} ${attributeString}` : display_name;
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
export function loadAllImages(el) {
    const images = el.querySelectorAll("img");
    return Promise.all(Array.from(images).map(img => loadImage(img.src)));
}
