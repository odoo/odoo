import { parseDateTime, deserializeDate } from "@web/core/l10n/dates";
import { roundDecimals, floatIsZero } from "@web/core/utils/numbers";

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
                    attributeString += `${value.attribute_id.name}: ${value.name}: ${customValue.custom_value}, `;
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
    if (!channel || typeof channel !== "string") {
        return () => false;
    }

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
    if (!el) {
        return Promise.resolve();
    }

    const images = el.querySelectorAll("img");
    return Promise.all(Array.from(images).map((img) => loadImage(img.src)));
}
export function parseUTCString(utcStr) {
    return parseDateTime(utcStr, { format: "yyyy-MM-dd HH:mm:ss", tz: "utc" });
}

export function floatCompare(a, b, { decimals } = {}) {
    if (decimals === undefined) {
        throw new Error("decimals must be provided");
    }
    a = roundDecimals(a, decimals);
    b = roundDecimals(b, decimals);
    const delta = a - b;
    if (floatIsZero(delta, decimals)) {
        return 0;
    }
    return delta < 0 ? -1 : 1;
}

export function gte(a, b, { decimals } = {}) {
    return floatCompare(a, b, { decimals }) >= 0;
}

export function gt(a, b, { decimals } = {}) {
    return floatCompare(a, b, { decimals }) > 0;
}

export function lte(a, b, { decimals } = {}) {
    return floatCompare(a, b, { decimals }) <= 0;
}

export function lt(a, b, { decimals } = {}) {
    return floatCompare(a, b, { decimals }) < 0;
}

export function computeProductPricelistCache(service, data = []) {
    // This function is called via the addEventListener callback initiated in the
    // processServerData function when new products or pricelists are loaded into the PoS.
    // It caches the heavy pricelist calculation when there are many products and pricelists.
    const date = luxon.DateTime.now();
    let pricelistItems = service.models["product.pricelist.item"].getAll();
    let products = service.models["product.product"].getAll();

    if (data.length > 0) {
        if (data[0].model.modelName === "product.product") {
            products = data;
        }

        if (data[0].model.modelName === "product.pricelist.item") {
            pricelistItems = data;
            // it needs only to compute for the products that are affected by the pricelist items
            const productTmplIds = new Set(data.map((item) => item.raw.product_tmpl_id));
            const productIds = new Set(data.map((item) => item.raw.product_id));
            products = products.filter(
                (product) =>
                    productTmplIds.has(product.raw.product_tmpl_id) || productIds.has(product.id)
            );
        }
    }

    const pushItem = (targetArray, key, item) => {
        if (!targetArray[key]) {
            targetArray[key] = [];
        }
        targetArray[key].push(item);
    };

    const pricelistRules = {};

    for (const item of pricelistItems) {
        if (
            (item.date_start && deserializeDate(item.date_start) > date) ||
            (item.date_end && deserializeDate(item.date_end) < date)
        ) {
            continue;
        }
        const pricelistId = item.pricelist_id.id;

        if (!pricelistRules[pricelistId]) {
            pricelistRules[pricelistId] = {
                productItems: {},
                productTmlpItems: {},
                categoryItems: {},
                globalItems: [],
            };
        }

        const productId = item.raw.product_id;
        if (productId) {
            pushItem(pricelistRules[pricelistId].productItems, productId, item);
            continue;
        }
        const productTmplId = item.raw.product_tmpl_id;
        if (productTmplId) {
            pushItem(pricelistRules[pricelistId].productTmlpItems, productTmplId, item);
            continue;
        }
        const categId = item.raw.categ_id;
        if (categId) {
            pushItem(pricelistRules[pricelistId].categoryItems, categId, item);
        } else {
            pricelistRules[pricelistId].globalItems.push(item);
        }
    }

    for (const product of products) {
        const applicableRules = product.getApplicablePricelistRules(pricelistRules);
        for (const pricelistId in applicableRules) {
            if (product.cachedPricelistRules[pricelistId]) {
                const existingRuleIds = product.cachedPricelistRules[pricelistId].map(
                    (rule) => rule.id
                );
                const newRules = applicableRules[pricelistId].filter(
                    (rule) => !existingRuleIds.includes(rule.id)
                );
                product.cachedPricelistRules[pricelistId] = [
                    ...newRules,
                    ...product.cachedPricelistRules[pricelistId],
                ];
            } else {
                product.cachedPricelistRules[pricelistId] = applicableRules[pricelistId];
            }
        }
    }
    if (data.length > 0 && data[0].model.modelName === "product.product") {
        service._loadMissingPricelistItems(products);
    }
}
