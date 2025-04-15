/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { throttleForAnimation } from "@web/core/utils/timing";
import { BlockUI } from "./block_ui";
import { browser } from "@web/core/browser/browser";
import { getTabableElements } from "@web/core/utils/ui";
import { getActiveHotkey } from "../hotkeys/hotkey_service";

import { EventBus, reactive, useEffect, useRef } from "@odoo/owl";

export const SIZES = { XS: 0, VSM: 1, SM: 2, MD: 3, LG: 4, XL: 5, XXL: 6 };

function getFirstAndLastTabableElements(el) {
    const tabableEls = getTabableElements(el);
    return [tabableEls[0], tabableEls[tabableEls.length - 1]];
}

/**
 * This hook will set the UI active element
 * when the caller component will mount/patch and
 * only if the t-reffed element has some tabable elements.
 *
 * The caller component could pass a `t-ref` value of its template
 * to delegate the UI active element to another element than itself.
 *
 * @param {string} refName
 */
export function useActiveElement(refName) {
    if (!refName) {
        throw new Error("refName not given to useActiveElement");
    }
    const uiService = useService("ui");
    const ref = useRef(refName);

    function trapFocus(e) {
        const hotkey = getActiveHotkey(e);
        if (!["tab", "shift+tab"].includes(hotkey)) {
            return;
        }
        const el = e.currentTarget;
        const [firstTabableEl, lastTabableEl] = getFirstAndLastTabableElements(el);
        switch (hotkey) {
            case "tab":
                if (document.activeElement === lastTabableEl) {
                    firstTabableEl.focus();
                    e.preventDefault();
                    e.stopPropagation();
                }
                break;
            case "shift+tab":
                if (document.activeElement === firstTabableEl) {
                    lastTabableEl.focus();
                    e.preventDefault();
                    e.stopPropagation();
                }
                break;
        }
    }

    useEffect(
        (el) => {
            if (el) {
                const [firstTabableEl] = getFirstAndLastTabableElements(el);
                if (!firstTabableEl) {
                    // no tabable elements: no need to trap focus nor become the UI active element
                    return;
                }
                const oldActiveElement = document.activeElement;
                uiService.activateElement(el);

                el.addEventListener("keydown", trapFocus);

                if (!el.contains(document.activeElement)) {
                    firstTabableEl.focus();
                }
                return async () => {
                    // Components are destroyed from top to bottom, meaning that this cleanup is
                    // called before the ones of children. As a consequence, event handlers added on
                    // the current active element in children aren't removed yet, and can thus be
                    // executed if we deactivate that active element right away (e.g. the blur and
                    // change events could be triggered). For that reason, we wait for a micro-tick.
                    await Promise.resolve();
                    uiService.deactivateElement(el);
                    el.removeEventListener("keydown", trapFocus);

                    /**
                     * In some cases, the current active element is not
                     * anymore in el (e.g. with ConfirmationDialog, the
                     * confirm button is disabled when clicked, so the
                     * focus is lost). In that case, we also want to restore
                     * the focus to the previous active element so we
                     * check if the current active element is the body
                     */
                    if (
                        el.contains(document.activeElement) ||
                        document.activeElement === document.body
                    ) {
                        oldActiveElement.focus();
                    }
                };
            }
        },
        () => [ref.el]
    );
}

// window size handling
export const MEDIAS_BREAKPOINTS = [
    { maxWidth: 474 },
    { minWidth: 475, maxWidth: 575 },
    { minWidth: 576, maxWidth: 767 },
    { minWidth: 768, maxWidth: 991 },
    { minWidth: 992, maxWidth: 1199 },
    { minWidth: 1200, maxWidth: 1533 },
    { minWidth: 1534 },
];

/**
 * Create the MediaQueryList used both by the uiService and config from
 * `MEDIA_BREAKPOINTS`.
 *
 * @returns {MediaQueryList[]}
 */
export function getMediaQueryLists() {
    return MEDIAS_BREAKPOINTS.map(({ minWidth, maxWidth }) => {
        if (!maxWidth) {
            return window.matchMedia(`(min-width: ${minWidth}px)`);
        }
        if (!minWidth) {
            return window.matchMedia(`(max-width: ${maxWidth}px)`);
        }
        return window.matchMedia(`(min-width: ${minWidth}px) and (max-width: ${maxWidth}px)`);
    });
}

// window size handling.
const MEDIAS = getMediaQueryLists();

export const utils = {
    getSize() {
        return MEDIAS.findIndex((media) => media.matches);
    },
    isSmall(ui = {}) {
        return (ui.size || utils.getSize()) <= SIZES.SM;
    },
};

const bus = new EventBus();

export function listenSizeChange(callback) {
    bus.addEventListener("resize", callback);
    return () => bus.removeEventListener("resize", callback);
}

export const uiService = {
    start(env) {
        // block/unblock code
        registry.category("main_components").add("BlockUI", { Component: BlockUI, props: { bus } });

        let blockCount = 0;
        function block(data) {
            blockCount++;
            if (blockCount === 1) {
                bus.trigger("BLOCK", {
                    message: data?.message,
                });
            }
        }
        function unblock() {
            blockCount--;
            if (blockCount < 0) {
                console.warn(
                    "Unblock ui was called more times than block, you should only unblock the UI if you have previously blocked it."
                );
                blockCount = 0;
            }
            if (blockCount === 0) {
                bus.trigger("UNBLOCK");
            }
        }

        // UI active element code
        let activeElems = [document];

        function activateElement(el) {
            activeElems.push(el);
            bus.trigger("active-element-changed", el);
        }
        function deactivateElement(el) {
            activeElems = activeElems.filter((x) => x !== el);
            bus.trigger("active-element-changed", ui.activeElement);
        }
        function getActiveElementOf(el) {
            for (const activeElement of [...activeElems].reverse()) {
                if (activeElement.contains(el)) {
                    return activeElement;
                }
            }
        }

        const ui = reactive({
            bus,
            size: utils.getSize(),
            get activeElement() {
                return activeElems[activeElems.length - 1];
            },
            get isBlocked() {
                return blockCount > 0;
            },
            isSmall: utils.isSmall(),
            block,
            unblock,
            activateElement,
            deactivateElement,
            getActiveElementOf,
        });

        // listen to media query status changes
        const updateSize = () => {
            const prevSize = ui.size;
            ui.size = utils.getSize();
            if (ui.size !== prevSize) {
                ui.isSmall = utils.isSmall(ui);
                bus.trigger("resize");
            }
        };
        browser.addEventListener("resize", throttleForAnimation(updateSize));

        Object.defineProperty(env, "isSmall", {
            get() {
                return ui.isSmall;
            },
        });

        return ui;
    },
};

registry.category("services").add("ui", uiService);
