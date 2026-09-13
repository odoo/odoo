// @ts-check
/** @odoo-module native */

import { useEffect, useRef } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/browser/hotkeys";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useOwnedActiveElement } from "@web/core/utils/active_element_scope";
import {
    getActiveElement,
    getDeepActiveElement,
    getTabableElements,
    isFocusable,
} from "@web/core/utils/dom/ui";
import { useService } from "@web/core/utils/hooks";
import { describeNode } from "@web/ui/describe_node";

const log = makeLogger("web.ui.focus");

/**
 * @param {HTMLElement} el
 * @returns {[HTMLElement | undefined, HTMLElement | undefined]}
 */
export function getFirstAndLastTabableElements(el) {
    const tabableEls = getTabableElements(el);
    return [tabableEls[0], tabableEls.at(-1)];
}

/** @param {KeyboardEvent} e */
function trapFocus(e) {
    const hotkey = getActiveHotkey(e);
    if (!["tab", "shift+tab"].includes(hotkey)) {
        return;
    }
    const el = /** @type {HTMLElement} */ (e.currentTarget);
    const [firstTabableEl, lastTabableEl] = getFirstAndLastTabableElements(el);
    if (!firstTabableEl && !lastTabableEl) {
        e.preventDefault();
        e.stopPropagation();
        return;
    }
    switch (hotkey) {
        case "tab":
            if (getDeepActiveElement(el) === lastTabableEl) {
                firstTabableEl?.focus();
                e.preventDefault();
                e.stopPropagation();
            }
            break;
        case "shift+tab":
            if (getDeepActiveElement(el) === firstTabableEl) {
                lastTabableEl?.focus();
                e.preventDefault();
                e.stopPropagation();
            }
            break;
    }
}

/** @param {string} refName */
export function useActiveElement(refName) {
    if (!refName) {
        throw new Error("refName not given to useActiveElement");
    }
    const uiService = useService("ui");
    const ref = useRef(refName);
    const scope = useOwnedActiveElement();

    useEffect(
        (el) => {
            if (el) {
                const [firstTabableEl] = getFirstAndLastTabableElements(el);
                const takesFocus = Boolean(firstTabableEl) || isFocusable(el);
                const oldActiveElement =
                    getDeepActiveElement(el) ?? getDeepActiveElement(el.ownerDocument);
                scope.el = el;
                uiService.activateElement(el);

                el.addEventListener("keydown", trapFocus);

                let focused = "kept";
                if (firstTabableEl) {
                    if (!el.contains(getActiveElement(el))) {
                        firstTabableEl.focus();
                        focused = "firstTabable";
                    }
                } else if (isFocusable(el) && el !== getActiveElement(el)) {
                    el.focus();
                    focused = "self";
                }
                log.logic("activate", () => ({
                    el: describeNode(el),
                    takesFocus,
                    focused,
                    from: describeNode(oldActiveElement),
                }));
                return () => {
                    scope.el = null;
                    uiService.deactivateElement(el);
                    el.removeEventListener("keydown", trapFocus);

                    let restored = "none";
                    if (
                        takesFocus &&
                        (el.contains(getActiveElement(el)) ||
                            getActiveElement(el) === el.ownerDocument.body)
                    ) {
                        if (oldActiveElement?.isConnected) {
                            /** @type {HTMLElement} */ (oldActiveElement).focus();
                            restored = "previous";
                        } else {
                            const [firstTabableEl] = getFirstAndLastTabableElements(
                                /** @type {HTMLElement} */ (uiService.activeElement),
                            );
                            firstTabableEl?.focus();
                            restored = firstTabableEl
                                ? "activeFirstTabable"
                                : "nothing";
                        }
                    }
                    log.logic("deactivate", () => ({
                        el: describeNode(el),
                        restored,
                        to: describeNode(getDeepActiveElement(el.ownerDocument)),
                    }));
                };
            }
        },
        () => [ref.el],
    );
}
