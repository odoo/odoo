// @ts-check

/**
 * Polyfill for the ClipboardItem constructor for browsers that partially
 * implement the Clipboard API (e.g. Firefox with write() behind a flag).
 */
class ClipboardItemImpl {
    /**
     * @param {Record<string, Blob>} items MIME-type → Blob map
     * @param {{ presentationStyle?: PresentationStyle }} [options]
     */
    constructor(items, options = {}) {
        this.items = items;
        this.options = options;
    }

    /** @returns {PresentationStyle | undefined} */
    get presentationStyle() {
        return this.options.presentationStyle;
    }

    /** @returns {string[]} */
    get types() {
        return Object.keys(this.items);
    }

    /**
     * @param {string} type
     * @returns {Blob | undefined}
     */
    getType(type) {
        return this.items[type];
    }
}

/**
 * Reads a Blob as a UTF-8 string.
 *
 * @param {Blob} blob
 * @returns {Promise<string>}
 */
function blobToStr(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.addEventListener("load", () => {
            const { result } = reader;
            if (typeof result === "string") {
                resolve(result);
            } else {
                reject("Cannot read Blob as String");
            }
        });
        reader.addEventListener("error", () => {
            reject("Cannot read Blob");
        });
        reader.readAsText(blob);
    });
}

/**
 * Converts all blobs in a ClipboardItem to strings.
 *
 * @param {ClipboardItemImpl} item
 * @returns {Promise<Record<string, string>>}
 */
async function stringify(item) {
    const strItem = /** @type {Record<string, string>} */ ({});
    for (const type of item.types) {
        strItem[type] = await blobToStr(item.getType(type));
    }
    return strItem;
}

/**
 * Polyfill for `navigator.clipboard.write()` using `execCommand('copy')`.
 *
 * @param {ClipboardItemImpl[]} items
 * @returns {Promise<any>}
 */
async function write(items) {
    if (!items[0].getType("text/plain")) {
        throw new Error(
            `Calling clipboard.write() without a "text/plain" type may result in an empty clipboard on some platforms.`,
        );
    }
    const strItem = await stringify(items[0]);

    const stubContainer = document.createElement("div");
    const shadowContainer = stubContainer.attachShadow({ mode: "open" });
    const stub = document.createElement("span");
    stub.innerText = strItem["text/plain"];
    shadowContainer.appendChild(stub);
    document.body.appendChild(stubContainer);

    const selection = document.getSelection();
    const range = document.createRange();
    range.selectNodeContents(stub);
    selection.removeAllRanges();
    selection.addRange(range);

    const onCopy = (ev) => {
        for (const type in strItem) {
            ev.clipboardData.setData(type, strItem[type]);
        }
        ev.preventDefault();
    };
    document.addEventListener("copy", onCopy);
    let result;
    try {
        result = document.execCommand("copy");
    } finally {
        document.removeEventListener("copy", onCopy);
    }

    selection.removeAllRanges();
    document.body.removeChild(stubContainer);

    return result;
}

/**
 * Only attempt to polyfill browsers that partially implement
 * the Clipboard API (aka. Firefox with `clipboard.write()` and
 * `ClipboardItem` behind a feature flag)
 *
 * Spec: https://w3c.github.io/clipboard-apis/
 */
if (window.navigator.clipboard) {
    if (!window.navigator.clipboard.write) {
        window.navigator.clipboard.write = /** @type {any} */ (write.bind(window));
    }
    if (!window.ClipboardItem) {
        // ClipboardItemImpl satisfies the ClipboardItem interface at runtime
        window.ClipboardItem = /** @type {any} */ (ClipboardItemImpl);
    }
}
