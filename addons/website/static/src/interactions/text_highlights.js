import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import {
    getCurrentTextHighlight,
    adaptHighlightPosition,
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
            const descendantEls = closestToObserve.querySelectorAll(".o_text_highlight");
            const highlightEls = closestToObserve.matches(".o_text_highlight")
                ? [closestToObserve, ...descendantEls]
                : descendantEls;
            for (const el of highlightEls) {
                const highlightID = getCurrentTextHighlight(el);
                const currentSVGs = el.querySelectorAll(".o_text_highlight_svg");
                for (const svg of currentSVGs) {
                    svg.remove();
                }
                withAnimationsAtEnd(el, () => {
                    const svgs = makeHighlightSvgs(el, highlightID);

                    for (const svg of svgs.toReversed()) {
                        this.insert(svg, el, "afterbegin");
                        adaptHighlightPosition(el, svg);
                    }
                });
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

/**
 * While an animation is running, an element may be moving, resizing, or
 * rotating. If we measure it at that moment, we get its temporary size and
 * position instead of its final ones. The highlight SVGs use these measurements
 * and keep that shape. So, if they are created during an animation, they may
 * end up using a temporary shape. To avoid this, the animations are briefly
 * reset before taking measurements and then restored before the browser shows
 * the next frame. The visitor does not notice this, and no HTML is changed.
 *
 * @param {HTMLElement} el
 * @param {Function} callback
 */
function withAnimationsAtEnd(el, callback) {
    const currentTimes = new Map();
    for (const animation of el.ownerDocument.getAnimations()) {
        const targetEl = animation.effect?.target;
        if (!(targetEl?.contains(el) || el.contains(targetEl))) {
            continue;
        }
        currentTimes.set(animation, animation.currentTime);
        animation.currentTime = animation.effect.getComputedTiming().endTime;
    }
    try {
        callback();
    } finally {
        for (const [animation, currentTime] of currentTimes) {
            animation.currentTime = currentTime;
        }
    }
}

registry.category("public.interactions").add("website.text_highlight", TextHighlight);

registry.category("public.interactions.edit").add("website.text_highlight", {
    Interaction: TextHighlight,
});
