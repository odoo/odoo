import { markup, reactive } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { escape } from "@web/core/utils/strings";

const Markup = markup().constructor;

export function assignDefined(obj, data, keys = Object.keys(data)) {
    for (const key of keys) {
        if (data[key] !== undefined) {
            obj[key] = data[key];
        }
    }
    return obj;
}

export function assignIn(obj, data, keys = Object.keys(data)) {
    for (const key of keys) {
        if (key in data) {
            obj[key] = data[key];
        }
    }
    return obj;
}

export const mailGlobal = {
    isInTest: false,
};

/**
 * Use `rpc` instead.
 *
 * @deprecated
 */
export function rpcWithEnv() {
    return rpc;
}

// todo: move this some other place in the future
export function isDragSourceExternalFile(dataTransfer) {
    const dragDataType = dataTransfer.types;
    if (dragDataType.constructor === window.DOMStringList) {
        return dragDataType.contains("Files");
    }
    if (dragDataType.constructor === Array) {
        return dragDataType.includes("Files");
    }
    return false;
}

/**
 * @param {Object} target
 * @param {string|string[]} key
 * @param {Function} callback
 */
export function onChange(target, key, callback) {
    let proxy;
    function _observe() {
        // access proxy[key] only once to avoid triggering reactive get() many times
        const val = proxy[key];
        if (typeof val === "object" && val !== null) {
            void Object.keys(val);
        }
        if (Array.isArray(val)) {
            void val.length;
            void val.forEach((i) => i);
        }
    }
    if (Array.isArray(key)) {
        for (const k of key) {
            onChange(target, k, callback);
        }
        return;
    }
    proxy = reactive(target, () => {
        _observe();
        callback();
    });
    _observe();
    return proxy;
}

/**
 * @param {MediaStream} [stream]
 */
export function closeStream(stream) {
    stream?.getTracks?.().forEach((track) => track.stop());
}

/**
 * Compare two Luxon datetime.
 *
 * @param {import("@web/core/l10n/dates").NullableDateTime} date1
 * @param {import("@web/core/l10n/dates").NullableDateTime} date2
 * @returns {number} Negative if date1 is less than date2, positive if date1 is
 *  greater than date2, and 0 if they are equal.
 */
export function compareDatetime(date1, date2) {
    if (date1?.ts === date2?.ts) {
        return 0;
    }
    if (!date1) {
        return -1;
    }
    if (!date2) {
        return 1;
    }
    return date1.ts - date2.ts;
}

/**
 * Compares two version strings.
 *
 * @param {string} v1 - The first version string to compare.
 * @param {string} v2 - The second version string to compare.
 * @return {number} -1 if v1 is less than v2, 1 if v1 is greater than v2, and 0 if they are equal.
 */
function compareVersion(v1, v2) {
    const parts1 = v1.split(".");
    const parts2 = v2.split(".");

    for (let i = 0; i < Math.max(parts1.length, parts2.length); i++) {
        const num1 = parseInt(parts1[i]) || 0;
        const num2 = parseInt(parts2[i]) || 0;
        if (num1 < num2) {
            return -1;
        }
        if (num1 > num2) {
            return 1;
        }
    }
    return 0;
}

/**
 * Return a version object that can be compared to other version strings.
 *
 * @param {string} v The version string to evaluate.
 */
export function parseVersion(v) {
    return {
        isLowerThan(other) {
            return compareVersion(v, other) < 0;
        },
    };
}

/**
 * Applies list join on content and returns a markup result built for HTML.
 *
 * @param {Array<string|ReturnType<markup>>} args
 * @returns {ReturnType<markup>}
 */
export function markupHtmlJoin(...args) {
    return markup(args.map((arg) => (arg instanceof Markup ? arg : escape(arg))).join(""));
}

/**
 * Applies string replace on content and returns a markup result built for HTML.
 *
 * @param {string|ReturnType<markup} content
 * @param {string | RegExp} search
 * @param {string} replacement
 * @returns {ReturnType<markup>}
 */
export function markupHtmlReplace(content, search, replacement) {
    if (!(content instanceof Markup)) {
        content = markup(escape(content));
    }
    if ((typeof search === "string" || search instanceof String) && !(search instanceof Markup)) {
        search = markup(escape(search));
    }
    if (!(replacement instanceof Markup)) {
        replacement = markup(escape(replacement));
    }
    return markup(content.replace(search, replacement));
}

/**
 * Applies string slice on content and returns a markup result built for HTML.
 *
 * @param {string|ReturnType<markup>} content
 * @returns {string|ReturnType<markup>}
 */
export function markupHtmlTrim(content) {
    if (!(content instanceof Markup)) {
        content = markup(escape(content));
    }
    return markup(content.trim());
}

/**
 * @param {Element} node
 * @param {string|ReturnType<markup>} content
 */
export function setElementContent(node, content) {
    if (content instanceof Markup) {
        node.innerHTML = content;
    } else {
        node.textContent = content;
    }
}

/**
 * @param {string|ReturnType<markup>} content
 */
export function createDocumentFragmentFromContent(content) {
    const div = document.createElement("div");
    setElementContent(div, content);
    return new DOMParser().parseFromString(div.innerHTML, "text/html");
}
