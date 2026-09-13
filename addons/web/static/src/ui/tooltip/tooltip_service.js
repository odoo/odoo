// @ts-check
/** @odoo-module native */

import { whenReady } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { hasTouch } from "@web/core/browser/feature_detection";
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { warnUnknownOptions } from "@web/ui/overlay/presenter";
import { watchForDetachedTarget } from "@web/ui/popover/detached_target_watcher";
import { Tooltip } from "@web/ui/tooltip/tooltip";

export const OPEN_DELAY = 400;
export const SHOW_AFTER_DELAY = 250;

const TOOLTIP_PARAMS = new Set(["delay", "info", "position", "template", "tooltip"]);

let nextTooltipId = 1;

const TOOLTIP_HOLDER_SELECTOR = "[data-tooltip], [data-tooltip-template]";

/**
 * @param {EventTarget | Node | null} node
 * @returns {HTMLElement | null}
 */
function tooltipHolderOf(node) {
    const el = /** @type {Element | null} */ (node);
    if (!el || el.nodeType !== Node.ELEMENT_NODE) {
        return null;
    }
    return /** @type {HTMLElement | null} */ (el.closest(TOOLTIP_HOLDER_SELECTOR));
}

class TrackedTooltip {
    /**
     * @param {HTMLElement} el
     * @param {() => void} onDetached
     */
    constructor(el, onDetached) {
        this.el = el;
        /** @type {number | undefined} */
        this.openTimeout = undefined;
        /** @type {(() => void) | null} */
        this.closePopover = null;
        /** @type {string | null} */
        this.borrowedDescribedBy = null;
        /** @type {string | null} */
        this.tooltipId = null;

        this.borrowedTitle = el.getAttribute("title");
        if (this.borrowedTitle !== null) {
            el.removeAttribute("title");
        }
        /** @type {(() => void) | null} */
        this.unwatch = watchForDetachedTarget(el, onDetached);
    }

    /** @returns {string} */
    describe() {
        const tooltipId = `o_tooltip_${nextTooltipId++}`;
        this.borrowedDescribedBy = this.el.getAttribute("aria-describedby");
        this.tooltipId = tooltipId;
        this.el.setAttribute(
            "aria-describedby",
            this.borrowedDescribedBy
                ? `${this.borrowedDescribedBy} ${tooltipId}`
                : tooltipId,
        );
        return tooltipId;
    }

    release() {
        if (this.borrowedTitle !== null) {
            if (!this.el.hasAttribute("title")) {
                this.el.setAttribute("title", this.borrowedTitle);
            }
            this.borrowedTitle = null;
        }
        if (this.tooltipId !== null) {
            const current = this.el.getAttribute("aria-describedby");
            const borrowed = this.borrowedDescribedBy;
            const installed = borrowed
                ? `${borrowed} ${this.tooltipId}`
                : this.tooltipId;
            if (current === installed) {
                if (borrowed === null) {
                    this.el.removeAttribute("aria-describedby");
                } else {
                    this.el.setAttribute("aria-describedby", borrowed);
                }
            } else if (current?.split(/\s+/).includes(this.tooltipId)) {
                const remaining = current
                    .split(/\s+/)
                    .filter((id) => id && id !== this.tooltipId);
                if (remaining.length) {
                    this.el.setAttribute("aria-describedby", remaining.join(" "));
                } else {
                    this.el.removeAttribute("aria-describedby");
                }
            }
            this.borrowedDescribedBy = null;
            this.tooltipId = null;
        }
        this.unwatch?.();
        this.unwatch = null;
        browser.clearTimeout(this.openTimeout);
        this.openTimeout = undefined;
        const closePopover = this.closePopover;
        this.closePopover = null;
        closePopover?.();
    }
}

const log = makeLogger("web.ui.tooltip");

class TooltipService {
    /** @param {{ popover: any }} services */
    constructor({ popover }) {
        this.popover = popover;
        /** @type {TrackedTooltip | null} */
        this.tracked = null;
        /** @type {number | undefined} */
        this.showTimer = undefined;
        this.elementsWithTooltips = new WeakMap();
        /** @type {(() => void)[]} */
        this.listenerDisposers = [];
        this.destroyed = false;

        whenReady(() => {
            if (this.destroyed) {
                return;
            }
            if (hasTouch()) {
                this.addBodyListener("touchstart", (ev) => this.onTouchStart(ev));
                this.addBodyListener("touchend", (ev) => this.onTouchEnd(ev));
                this.addBodyListener("touchcancel", (ev) => this.onTouchEnd(ev));
            }

            this.addBodyListener("mouseenter", (ev) => this.onMouseenter(ev), {
                capture: true,
            });
            this.addBodyListener("mouseleave", (ev) => this.cleanupTooltip(ev), {
                capture: true,
            });
            this.addBodyListener("focusin", (ev) => this.onFocusin(ev), {
                capture: true,
            });
            this.addBodyListener("focusout", (ev) => this.cleanupTooltip(ev), {
                capture: true,
            });
            this.addBodyListener("click", (ev) => this.onClick(ev), { capture: true });
        });
    }

    /**
     * @param {HTMLElement} el
     * @return {boolean}
     */
    isHelpNode(el) {
        return (
            el.textContent === "?" &&
            (el.hasAttribute("data-tooltip") ||
                el.hasAttribute("data-tooltip-template"))
        );
    }

    cleanup() {
        const released = this.tracked;
        this.tracked = null;
        released?.release();
        browser.clearTimeout(this.showTimer);
    }

    /**
     * @param {HTMLElement} el
     * @param {object} param1
     * @param {string} [param1.tooltip]
     * @param {string} [param1.template]
     * @param {object} [param1.info]
     * @param {'top'|'bottom'|'left'|'right'} param1.position
     * @param {number} [param1.delay]
     */
    openTooltip(el, { tooltip = "", template, info, position, delay = OPEN_DELAY }) {
        log.lifecycle("open", () => ({
            tag: el.tagName,
            tooltip,
            template,
            position,
            delay,
        }));
        this.cleanup();
        if (!tooltip && !template) {
            return;
        }

        const opening = new TrackedTooltip(el, () => this.cleanup());
        this.tracked = opening;
        const timeoutDelay = this.isHelpNode(el) ? 0 : delay;
        opening.openTimeout = browser.setTimeout(() => {
            opening.openTimeout = undefined;
            log.lifecycle("show", () => ({
                tag: el.tagName,
                connected: el.isConnected,
            }));
            if (!el.isConnected) {
                return;
            }
            opening.closePopover = this.popover.add(
                el,
                Tooltip,
                { tooltip, template, info, id: opening.describe() },
                {
                    position,
                    onClose: () => {
                        if (this.tracked === opening) {
                            opening.closePopover = null;
                            this.cleanup();
                        }
                    },
                },
            );
        }, timeoutDelay);
    }

    /** @param {HTMLElement} el */
    openElementsTooltip(el) {
        const element = tooltipHolderOf(el);
        if (!element && !this.elementsWithTooltips.has(el)) {
            return;
        }
        if (this.tracked && (this.tracked.el === el || this.tracked.el === element)) {
            return;
        }
        if (this.elementsWithTooltips.has(el)) {
            this.openTooltip(el, this.elementsWithTooltips.get(el));
        } else if (element) {
            const dataset = element.dataset;
            /** @type {Record<string, any>} */
            const params = {
                tooltip: dataset.tooltip,
                template: dataset.tooltipTemplate,
                position: dataset.tooltipPosition,
            };
            if (dataset.tooltipInfo) {
                try {
                    params.info = JSON.parse(dataset.tooltipInfo);
                } catch {
                    if (odoo.debug) {
                        console.warn(
                            "[tooltip] data-tooltip-info is not JSON; ignoring it.",
                            element,
                        );
                    }
                }
            }
            if (dataset.tooltipDelay) {
                const delay = Number.parseInt(dataset.tooltipDelay, 10);
                if (Number.isFinite(delay) && delay >= 0) {
                    params.delay = delay;
                }
            }
            this.openTooltip(element, /** @type {any} */ (params));
        }
    }

    /** @param {MouseEvent} ev */
    onMouseenter(ev) {
        this.openElementsTooltip(/** @type {HTMLElement} */ (ev.target));
    }

    /** @param {FocusEvent} ev */
    onFocusin(ev) {
        this.openElementsTooltip(/** @type {HTMLElement} */ (ev.target));
    }

    /**
     * @param {HTMLElement} el
     * @returns {boolean}
     */
    isTapToShow(el) {
        if (!hasTouch()) {
            return false;
        }
        return Boolean(tooltipHolderOf(el)?.dataset.tooltipTouchTapToShow);
    }

    /** @param {MouseEvent} ev */
    onClick(ev) {
        const el = /** @type {HTMLElement} */ (ev.target);
        if (this.isHelpNode(el)) {
            ev.preventDefault();
        }
        if (!this.tracked || this.isTapToShow(el)) {
            return;
        }
        if (this.tracked.el.contains(el) || this.tracked.openTimeout) {
            this.cleanup();
        }
    }

    cleanupTooltip(/** @type {Event} */ ev) {
        const el = this.tracked?.el;
        if (!el) {
            return;
        }
        const target = /** @type {Node | null} */ (ev.target);
        const relatedTarget = /** @type {FocusEvent | MouseEvent} */ (ev).relatedTarget;
        if (
            (el === target || (ev.type === "focusout" && el.contains(target))) &&
            !(relatedTarget instanceof Node && el.contains(relatedTarget))
        ) {
            log.lifecycle("leave", { type: ev.type });
            this.cleanup();
        }
    }
    /** @param {TouchEvent} ev */
    onTouchStart(ev) {
        this.cleanup();
        const el = /** @type {HTMLElement} */ (ev.target);
        const timeoutDelay = this.isHelpNode(el) ? 0 : SHOW_AFTER_DELAY;
        this.showTimer = browser.setTimeout(() => {
            this.openElementsTooltip(el);
        }, timeoutDelay);
    }

    /** @param {TouchEvent} ev */
    onTouchEnd(ev) {
        const el = /** @type {HTMLElement} */ (ev.target);
        if (this.isHelpNode(el)) {
            ev.preventDefault();
            return;
        }
        const holder = tooltipHolderOf(el);
        if (holder && !holder.dataset.tooltipTouchTapToShow) {
            browser.clearTimeout(this.showTimer);
            if (this.tracked?.openTimeout) {
                this.cleanup();
            }
        }
    }

    /**
     * @param {string} type
     * @param {(ev: any) => void} handler
     * @param {AddEventListenerOptions} [options]
     */
    addBodyListener(type, handler, options) {
        document.body.addEventListener(type, handler, options);
        this.listenerDisposers.push(() =>
            document.body.removeEventListener(type, handler, options),
        );
    }

    /**
     * @param {HTMLElement} el
     * @param {Record<string, any>} params
     * @returns {() => void}
     */
    add(el, params) {
        warnUnknownOptions("tooltip", params, TOOLTIP_PARAMS);
        this.elementsWithTooltips.set(el, params);
        return () => {
            this.elementsWithTooltips.delete(el);
            if (this.tracked?.el === el) {
                this.cleanup();
            }
        };
    }

    destroy() {
        this.destroyed = true;
        this.cleanup();
        for (const dispose of this.listenerDisposers) {
            dispose();
        }
        this.listenerDisposers.length = 0;
    }
}

const tooltipService = {
    dependencies: ["popover"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {{ popover: any }} services
     * @returns {TooltipService}
     */
    start(env, services) {
        return new TooltipService(services);
    },
};

registry.category("services").add("tooltip", tooltipService);
