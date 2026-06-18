import { effect, immediateEffect, plugin, proxy, untrack, useEffect, useScope } from "@odoo/owl";

import { AssetsLoadingError, getBundle } from "@web/core/assets";
import { memoize } from "@web/core/utils/functions";

/**
 * Version of plugin() where the plugin is allowed to not be provided by any parented component.
 *
 * @template T
 * @param {T extends import("@odoo/owl").PluginConstructor} pluginType
 * @returns {import("@odoo/owl").PluginInstance<T>|undefined}
 */
export function maybePlugin(pluginType) {
    if (useScope().pluginManager?.getPluginById(pluginType.id)) {
        return plugin(pluginType);
    }
    return undefined;
}

export function assignDefined(obj, data, keys = Object.keys(data)) {
    for (const key of keys) {
        if (data[key] !== undefined) {
            obj[key] = data[key];
        }
    }
    return obj;
}

export function assignGetter(obj, data) {
    const properties = Object.fromEntries(
        Object.entries(data).map(([getterName, getterFn]) => [
            getterName,
            {
                get: getterFn,
                set: () => {}, // avoids Proxy "trap returned falsish" error
            },
        ])
    );
    Object.defineProperties(obj, properties);
}

export function assignIn(obj, data, keys = Object.keys(data)) {
    for (const key of keys) {
        if (key in data) {
            obj[key] = data[key];
        }
    }
    return obj;
}

/**
 * @template T
 * @param {T[]} list
 * @param {number} target
 * @param {(item: T) => number} [itemToCompareVal]
 * @returns {T}
 */
export function nearestGreaterThanOrEqual(list, target, itemToCompareVal) {
    const findNext = (left, right, next) => {
        if (left > right) {
            return next;
        }
        const index = Math.floor((left + right) / 2);
        const item = list[index];
        const val = itemToCompareVal?.(item) ?? item;
        if (val === target) {
            return item;
        } else if (val > target) {
            return findNext(left, index - 1, item);
        } else {
            return findNext(index + 1, right, next);
        }
    };
    return findNext(0, list.length - 1, null);
}

export const mailGlobal = {
    isInTest: false,
};

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
 * @returns {Function} dispose function
 */
export function onChange(target, key, callback) {
    let targetProxy;
    function _observe() {
        // access targetProxy[key] only once to avoid triggering reactive get() many times
        const val = targetProxy[key];
        if (typeof val === "object" && val !== null) {
            void Object.keys(val);
        }
        if (Array.isArray(val)) {
            void val.length;
            void val.forEach((i) => i);
        }
    }
    if (Array.isArray(key)) {
        /** @type {Function[]} */
        const arrayDisposeFns = [];
        for (const k of key) {
            arrayDisposeFns.push(onChange(target, k, callback));
        }
        return () => {
            arrayDisposeFns.forEach((f) => f());
            arrayDisposeFns.length = 0;
        };
    }
    let running = false;
    targetProxy = proxy(target);
    const disposeFn = untrack(() =>
        immediateEffect(() => {
            _observe();
            if (running) {
                untrack(() => callback());
            }
        })
    );
    running = true;
    return disposeFn;
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
export function compareVersion(v1, v2) {
    const parts1 = v1.split(".");
    const parts2 = v2.split(".");

    for (let i = 0; i < Math.max(parts1.length, parts2.length); i++) {
        let rawPart1 = parts1[i];
        let rawPart2 = parts2[i];
        if (typeof rawPart1 === "string" && rawPart1.startsWith("saas~")) {
            rawPart1 = rawPart1.substring("saas~".length);
        }
        if (typeof rawPart2 === "string" && rawPart2.startsWith("saas~")) {
            rawPart2 = rawPart2.substring("saas~".length);
        }
        const num1 = parseInt(rawPart1) || 0;
        const num2 = parseInt(rawPart2) || 0;
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
 * Converts a given URL from platforms like YouTube, Google Drive, Instagram,
 * etc., into their embed format. This function extracts the necessary video ID
 * or content identifier from the input URL and returns the corresponding embed
 * URL for that platform.
 *
 * @param {string} url
 */
export function convertToEmbedURL(url) {
    const ytRegex = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|live\/|watch\?v=|&v=)([^#&?]*).*/;
    const ytMatch = url.match(ytRegex);
    if (ytMatch?.length === 3) {
        const youtubeURL = new URL(`/embed/${ytMatch[2]}`, "https://www.youtube.com");
        youtubeURL.searchParams.set("autoplay", "1");
        return { url: youtubeURL.toString(), provider: "youtube" };
    }
    const gdriveRegex = /(?:drive\.google\.com\/(?:file\/d\/|open\?id=|uc\?id=))([^/?&]+)/;
    const gdriveMatch = url.match(gdriveRegex);
    if (gdriveMatch?.length === 2) {
        const gdriveURL = new URL(`/file/d/${gdriveMatch[1]}/preview`, "https://drive.google.com");
        return { url: gdriveURL.toString(), provider: "google-drive" };
    }
    return { url: null, provider: null };
}

/**
 * Checks if the browser supports hardware acceleration for video processing.
 *
 * @returns {boolean} True if hardware acceleration is supported, false otherwise.
 */
export const hasHardwareAcceleration = memoize(() => {
    const canvas = document.createElement("canvas");
    const gl =
        canvas.getContext("webgl2") ||
        canvas.getContext("webgl") ||
        canvas.getContext("experimental-webgl");
    if (!gl) {
        // WebGL support is typically required for hardware acceleration.
        return false;
    }
    const debugInfo = gl.getExtension("WEBGL_debug_renderer_info");
    if (debugInfo) {
        const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
        if (/swiftshader|llvmpipe|software/i.test(renderer)) {
            // These renderers indicate software-based rendering instead of hardware acceleration.
            return false;
        }
    }
    return true;
});

/**
 * A hook that repeatedly calls a function with dynamically computed
 * intervals.
 *
 * @param {() => number|void} fn A callback that is invoked initially, after
 * signals, proxies, or computed values read during the callback change, or
 * when the delay has passed. Returning a falsy value cancels the interval.
 * Avoid reading reactive values that the callback itself writes unless they
 * are intended dependencies.
 */
export function useDynamicInterval(fn) {
    useEffect(() => {
        let timer;
        function tick() {
            const nextDelay = fn();
            if (nextDelay) {
                timer = setTimeout(tick, Math.ceil(nextDelay));
            }
        }
        tick();
        return () => clearTimeout(timer);
    });
}

/**
 * @param {() => void} effectFn
 * @returns {() => void} A function to dispose the effect then invoke last returned cleanup function
 */
export function effectWithCleanup(effectFn) {
    let cleanup;
    const disposeFn = effect(() => {
        untrack(() => cleanup?.());
        cleanup = effectFn();
    });
    return () => {
        disposeFn();
        untrack(() => cleanup?.());
    };
}

/**
 * @param {HTMLElement} targetNode
 * @param {string} bundleName
 */
export async function loadCssFromBundle(targetNode, bundleName) {
    try {
        const res = await getBundle(bundleName);
        for (const url of res.cssLibs) {
            const link = document.createElement("link");
            link.rel = "stylesheet";
            link.href = url;
            targetNode.appendChild(link);
            await new Promise((res, rej) => {
                link.addEventListener("load", res);
                link.addEventListener("error", rej);
            });
        }
    } catch (e) {
        if (e instanceof AssetsLoadingError && e.cause instanceof TypeError) {
            // an AssetsLoadingError caused by a TypeError means that the
            // fetch request has been cancelled by the browser. It can occur
            // when the user changes page, or navigate away from the website
            // client action, so the iframe is unloaded. In this case, we
            // don't care abour reporting the error, it is actually a normal
            // situation.
            return new Promise(() => {});
        } else {
            throw e;
        }
    }
}
