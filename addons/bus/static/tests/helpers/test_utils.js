/* @odoo-module */

import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { getFixture } from "@web/../tests/helpers/utils";

/**
 * Waits until exactly one element matching the given `selector` is present in
 * `options.target` and then clicks on it.
 *
 * @param {string} selector
 * @param {Object} [options={}] forwarded to `contains`
 */
export async function click(selector, options) {
    await contains(selector, { click: true, ...options });
}

/**
 * Waits until exactly one element matching the given `selector` is present in
 * `options.target` and then inserts the given `content`.
 *
 * @param {string} selector
 * @param {string} content
 * @param {Object} [options = {}]
 * @param {boolean} [options.replace=false]
 */
export async function insertText(selector, content, options = {}) {
    const { replace = false } = options;
    delete options.replace;
    const [target] = await contains(selector, options);
    target.focus();
    if (replace) {
        target.value = "";
        target.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Backspace" }));
        target.dispatchEvent(new window.KeyboardEvent("keyup", { key: "Backspace" }));
        target.dispatchEvent(new window.InputEvent("input"));
        target.dispatchEvent(new window.InputEvent("change"));
    }
    for (const char of content) {
        target.value += char;
        target.dispatchEvent(new window.KeyboardEvent("keydown", { key: char }));
        target.dispatchEvent(new window.KeyboardEvent("keyup", { key: char }));
        target.dispatchEvent(new window.InputEvent("input"));
        target.dispatchEvent(new window.InputEvent("change"));
    }
}

/**
 * Waits until exactly one element matching the given `selector` is present in
 * `options.target` and then sets its `scrollTop` to the given value.
 *
 * @param {string} selector
 * @param {number|"bottom"} scrollTop
 * @param {Object} [options={}] forwarded to `contains`
 */
export async function scroll(selector, scrollTop, options) {
    await contains(selector, { setScroll: scrollTop, ...options });
}

let hasUsedContainsPositively = false;
QUnit.testStart(() => (hasUsedContainsPositively = false));
/**
 * Waits until `count` elements matching the given `selector` are present in
 * `options.target`.
 *
 * @param {string} selector
 * @param {Object} [options={}]
 * @param {boolean} [options.click] if provided, clicks on the found element
 * @param {number} [count=1]
 * @param {number|"bottom"} [options.scroll] if provided, the scrollTop of the found element(s)
 *  must match.
 *  Note: when using one of the scrollTop options, it is advised to ensure the height is not going
 *  to change soon, by checking with a preceding contains that all the expected elements are in DOM.
 * @param {number|"bottom"} [options.setScroll] if provided, set the scrollTop on the found element
 * @param {HTMLElement} [options.target=getFixture()]
 * @param {string} [options.text] if provided, the textContent of the found element(s) must match.
 * @param {string} [options.value] if provided, the input value of the found element(s) must match.
 *  Note: value changes are not observed directly, another mutation must happen to catch them.
 * @returns {Promise<HTMLElement[]>}
 */
export function contains(
    selector,
    { click, count = 1, scroll, setScroll, target = getFixture(), text, value } = {}
) {
    if (count) {
        hasUsedContainsPositively = true;
    } else if (!hasUsedContainsPositively) {
        throw new Error(
            `Starting a test with "contains" of count 0 for selector "${selector}" is useless because it might immediately resolve. Start the test by checking that an expected element actually exists.`
        );
    }
    return new Promise((resolve, reject) => {
        const scrollListeners = new Set();
        let selectorMessage = `${count} of "${selector}"`;
        if (text !== undefined) {
            selectorMessage = `${selectorMessage} with text "${text}"`;
        }
        if (value !== undefined) {
            selectorMessage = `${selectorMessage} with value "${value}"`;
        }
        if (scroll !== undefined) {
            selectorMessage = `${selectorMessage} with scroll "${scroll}"`;
        }
        const res = select();
        if (res.length === count) {
            execute(res, "immediately");
            return;
        }
        let done = false;
        const timer = setTimeout(() => {
            clean();
            const res = select();
            const message = `Waited 5 second for ${selectorMessage}. Found ${res.length} instead.`;
            QUnit.assert.ok(false, message);
            reject(new Error(message));
        }, 5000);
        const observer = new MutationObserver(() => {
            const res = select();
            if (res.length === count) {
                clean();
                execute(res, "after mutations");
            }
        });
        observer.observe(document.body, {
            attributes: true,
            childList: true,
            subtree: true,
        });
        registerCleanup(() => {
            if (!done) {
                clean();
                const res = select();
                const message = `Test ended while waiting for ${selectorMessage}. Found ${res.length} instead.`;
                QUnit.assert.ok(false, message);
                reject(new Error(message));
            }
        });
        function onScroll(ev) {
            const res = select();
            if (res.length === count) {
                clean();
                execute(res, "after scroll");
            }
        }
        function select() {
            /** @type HTMLElement[] */
            let res;
            try {
                res = [...target.querySelectorAll(selector)];
            } catch (error) {
                if (error.message.includes("Failed to execute 'querySelectorAll'")) {
                    // keep jquery for backwards compatibility until all tests are converted
                    res = [...$(target).find(selector)];
                } else {
                    throw error;
                }
            }
            const filteredRes = res.filter(
                (el) =>
                    (text === undefined || el.textContent.trim() === text) &&
                    (value === undefined || el.value === value) &&
                    (scroll === undefined ||
                        (scroll === "bottom"
                            ? Math.abs(el.scrollHeight - el.clientHeight - el.scrollTop) <= 1
                            : Math.abs(el.scrollTop - scroll) <= 1))
            );
            if (
                scroll !== undefined &&
                !scrollListeners.size &&
                res.length === count &&
                filteredRes.length !== count
            ) {
                for (const el of res) {
                    scrollListeners.add(el);
                    el.addEventListener("scroll", onScroll);
                }
            }
            return filteredRes;
        }
        function execute(res, whenMessage) {
            let message = `Found ${selectorMessage} (${whenMessage})`;
            if (click) {
                message = `${message} and clicked it`;
                res[0].click();
            }
            if (setScroll !== undefined) {
                message = `${message} and set scroll to "${setScroll}"`;
                res[0].scrollTop = setScroll === "bottom" ? res[0].scrollHeight : setScroll;
            }
            QUnit.assert.ok(true, message);
            resolve(res);
        }
        function clean() {
            observer.disconnect();
            clearTimeout(timer);
            for (const el of scrollListeners) {
                el.removeEventListener("scroll", onScroll);
            }
            done = true;
        }
    });
}
