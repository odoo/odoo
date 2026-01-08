/** @odoo-module **/

class ClipboardItemImpl {
    constructor(items, options = {}) {
        this.items = items;
        this.options = options;
    }
    get presentationStyle() {
        return this.options.presentationStyle;
    }
    get types() {
        return Object.keys(this.items);
    }
    getType(type) {
        return this.items[type];
    }
}

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

async function stringify(item) {
    const strItem = {};
    for (const type of item.types) {
        strItem[type] = await blobToStr(item.getType(type));
    }
    return strItem;
}

async function write(items) {
    if (!items[0].getType("text/plain")) {
        throw new Error(
            `Calling clipboard.write() without a "text/plain" type may result in an empty clipboard on some platforms.`
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
        window.navigator.clipboard.write = write.bind(window);
    }
    if (!window.ClipboardItem) {
        window.ClipboardItem = ClipboardItemImpl;
    }
}
