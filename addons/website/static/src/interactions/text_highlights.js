import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { switchTextHighlight } from "@website/js/highlight_utils";

export class TextHighlight extends Interaction {
    static selector = "#wrapwrap";
    dynamicContent = {
        _root: {
            "t-on-text_highlight_added": ({target}) => this.onTextHighlightAdded(target),
        },
    };

    setup() {
        this.observerLock = new Map();
        this.observed = new WeakSet();
        this.resizeObserver = new window.ResizeObserver(this.updateEntries.bind(this));
        this.mutationObserver = new window.MutationObserver(this.updateEntries.bind(this));
    }

    start() {
        for (const textEl of this.el.querySelectorAll(".o_text_highlight")) {
            this.handleEl(textEl);
        }
    }

    destroy() {
        for (const svg of this.el.querySelectorAll(".o_text_highlight_svg")) {
            svg.remove();
        }
        this.resizeObserver.disconnect();
        this.mutationObserver.disconnect();
    }

    async updateEntries(entries) {
        await new Promise( r => requestAnimationFrame(r));
        if (this.isDestroyed) {
            return;
        }
        const closestToObserves = new Set();
        for (const { target, addedNodes = [], removedNodes = [] } of entries) {
            const elements = [target, ...(addedNodes), ...(removedNodes)]
                .map((el) => el.nodeType === Node.ELEMENT_NODE ? el : el.parentElement)
                .filter(Boolean);
            if (!elements.length) {
                continue;
            }
            const hasSvg = elements.some((el) => el.closest(".o_text_highlight_svg"));
            if (hasSvg) {
                continue;
            }
            closestToObserves.add(this.closestToObserve(target));
        }
        for (const closestToObserve of closestToObserves) {
            for (const el of closestToObserve.querySelectorAll(".o_text_highlight")) {
                switchTextHighlight(el);
            }
        }
    }
    /**
     * @param {HTMLElement} el
     */
    closestToObserve(el) {
        el = el.nodeType === Node.ELEMENT_NODE ? el : el.parentElement;
        if (!el || el === this.el) {
            return null;
        }
        if (window.getComputedStyle(el).display !== "inline") {
            return el;
        }
        return this.closestToObserve(el.parentElement);
    }

    /**
     * @param {HTMLElement} el
     */
    getObservedEls(el) {
        const closestToObserve = this.closestToObserve(el);
        return closestToObserve ? [closestToObserve, el] : [el];
    }

    /**
     * @param {HTMLElement} el
     */
    handleEl(el) {
        if (this.observed.has(el)) {
            return;
        }
        this.observed.add(el);
        // The `ResizeObserver` cannot detect the width change on highlight
        // units (`.o_text_highlight_item`) as long as the width of the entire
        // `.o_text_highlight` element remains the same, so we need to observe
        // each one of them and do the adjustment only once for the whole text.
        for (const elToObserve of this.getObservedEls(el)) {
            this.resizeObserver.observe(elToObserve);
        }
        const closestToObserve = this.closestToObserve(el);
        this.mutationObserver.observe(closestToObserve, {
            childList: true,
            characterData: true,
            subtree: true,
        });
        this.mutationObserver.observe(el, {
            attributes: true,
        });
        this.updateEntries([{ target: el }]);
    }

    /**
     * @param {HTMLElement} el
     */
    onTextHighlightAdded(el) {
        // todo: what was the purpose of this?
        // this.lockTextHighlightObserver(el);
        this.handleEl(el);
    }
}

registry
    .category("public.interactions")
    .add("website.text_highlight", TextHighlight);

registry
    .category("public.interactions.edit")
    .add("website.text_highlight", {
        Interaction: TextHighlight,
    });
