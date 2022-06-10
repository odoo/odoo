/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { debounce } from "@web/core/utils/timing";
import { BlockUI } from "./block_ui";
import { browser } from "@web/core/browser/browser";

const { EventBus, useEffect, useRef } = owl;

export const SIZES = { XS: 0, VSM: 1, SM: 2, MD: 3, LG: 4, XL: 5, XXL: 6 };

/**
 * This hook will set the UI active element
 * when the caller component will mount/unmount.
 *
 * The caller component could pass a `t-ref` value of its template
 * to delegate the UI active element to another element than itself.
 * In that case, it is mandatory that the referenced element is fixed and
 * not dynamically attached in/detached from the DOM (e.g. with t-if directive).
 *
 * @param {string} refName
 */
export function useActiveElement(refName) {
    if (!refName) {
        throw new Error("refName not given to useActiveElement");
    }
    const uiService = useService("ui");
    const owner = useRef(refName);
    useEffect(
        (el) => {
            if (el) {
                uiService.activateElement(el);
                return () => uiService.deactivateElement(el);
            }
        },
        () => [owner.el]
    );
}

// window size handling
export const MEDIAS_BREAKPOINTS = [
    { maxWidth: 474 },
    { minWidth: 475, maxWidth: 575 },
    { minWidth: 576, maxWidth: 767 },
    { minWidth: 769, maxWidth: 991 },
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

export const uiService = {
    getSize() {
        return MEDIAS.findIndex(media => media.matches);
    },
    start(env) {
        let ui = {};

        // block/unblock code
        const bus = new EventBus();
        registry.category("main_components").add("BlockUI", { Component: BlockUI, props: { bus } });

        let blockCount = 0;
        function block() {
            blockCount++;
            if (blockCount === 1) {
                bus.trigger("BLOCK");
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

        Object.assign(ui, {
            bus,
            block,
            unblock,
        });

        Object.defineProperty(ui, "isBlocked", {
            get() {
                return blockCount > 0;
            },
        });

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

        Object.assign(ui, {
            activateElement,
            deactivateElement,
            getActiveElementOf,
        });
        Object.defineProperty(ui, "activeElement", {
            get() {
                return activeElems[activeElems.length - 1];
            },
        });

        // listen to media query status changes
        function updateSize() {
            ui.size = this.getSize();
        }
        browser.addEventListener("resize", debounce(updateSize.bind(this), 100));

        Object.assign(ui, {
            size: this.getSize(),
        });
        Object.defineProperty(ui, "isSmall", {
            get() {
                return ui.size <= SIZES.SM;
            },
        });
        Object.defineProperty(env, "isSmall", {
            get() {
                return ui.size <= SIZES.SM;
            },
        });

        return ui;
    },
};

registry.category("services").add("ui", uiService);
