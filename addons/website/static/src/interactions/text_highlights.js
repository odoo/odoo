import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import {
    getCurrentTextHighlight,
    makeHighlightSvgs,
    closestToObserve,
    getObservedEls,
} from "@website/js/highlight_utils";

export class TextHighlight extends Interaction {
    static selector = "#wrapwrap, .o_wslides_fs_content";
    dynamicContent = {
        _root: {
            "t-on-text_highlight_added": ({ target }) => this.onTextHighlightAdded(target),
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
        this.resizeObserver.disconnect();
        this.mutationObserver.disconnect();
    }

    updateEntries(entries) {
        this.waitForAnimationFrame(() => this._updateEntries(entries));
    }
    _updateEntries(entries) {
        const closestToObserves = new Set();
        for (const { target, addedNodes = [], removedNodes = [] } of entries) {
            const elements = [target, ...addedNodes, ...removedNodes]
                .map((el) => (el.nodeType === Node.ELEMENT_NODE ? el : el.parentElement))
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
                const highlightID = getCurrentTextHighlight(el);
                const svgs = makeHighlightSvgs(el, highlightID);
                const currentSVGs = el.querySelectorAll(".o_text_highlight_svg");
                for (const svg of currentSVGs) {
                    svg.remove();
                }
                for (const svg of svgs) {
                    this.insert(svg, el);
                }
            }
        }
    }
    /**
     * TODO: Remove in master (left in stable for compatibility)
     *
     * @param {HTMLElement} el
     */
    closestToObserve(el) {
        return closestToObserve(el, this.el);
    }

    /**
     * TODO: Remove in master (left in stable for compatibility)
     *
     * @param {HTMLElement} el
     */
    getObservedEls(el) {
        return getObservedEls(el);
    }

    /**
     * @param {HTMLElement} el
     */
    handleEl(el) {
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

registry.category("public.interactions").add("website.text_highlight", TextHighlight);

registry.category("public.interactions.edit").add("website.text_highlight", {
    Interaction: TextHighlight,
});
