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

export function constructFullProductName(line) {
    let attributeString = "";

    if (line.attribute_value_ids && line.attribute_value_ids.length > 0) {
        for (const value of line.attribute_value_ids) {
            if (value.is_custom) {
                const customValue = line.custom_attribute_value_ids.find(
                    (cus) =>
                        cus.custom_product_template_attribute_value_id?.id == parseInt(value.id)
                );
                if (customValue) {
                    attributeString += `${value.attribute_id.name}: ${customValue.custom_value}, `;
                }
            } else {
                attributeString += `${value.name}, `;
            }
        }

        attributeString = attributeString.slice(0, -2);
        attributeString = ` (${attributeString})`;
    }

    return `${line?.product_id?.display_name}${attributeString}`;
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
export function loadAllImages(el) {
    const images = el.querySelectorAll("img");
    return Promise.all(Array.from(images).map((img) => loadImage(img.src)));
}

function match(pattern, text) {
    const rows = pattern.length + 1;
    const cols = text.length + 1;
    const scoreMatrix = [];

    for (let i = 0; i < rows; i++) {
        scoreMatrix[i] = new Array(cols).fill(0);
    }

    let maxScore = 0;

    // Calculate scores using Smith-Waterman algorithm
    for (let i = 1; i < rows; i++) {
        for (let j = 1; j < cols; j++) {
            const match = pattern[i - 1] === text[j - 1] ? 1 : -1;
            scoreMatrix[i][j] = Math.max(
                0,
                scoreMatrix[i - 1][j] - 1,
                scoreMatrix[i][j - 1] - 1,
                scoreMatrix[i - 1][j - 1] + match
            );

            if (scoreMatrix[i][j] > maxScore) {
                maxScore = scoreMatrix[i][j];
            }
        }
    }

    return maxScore / rows;
}

export function fuzzyLookup(pattern, list, fn) {
    const results = [];
    list.forEach((data) => {
        const text = fn(data);
        let score = match(pattern, text);
        // Phrase Match Bonus:
        if (text.includes(pattern)) {
            score += 0.3;
        }
        if (score > 0.3) {
            results.push({ score, elem: data });
        }
    });
    // we want better matches first
    results.sort((a, b) => b.score - a.score);
    return results.map((r) => r.elem);
}
