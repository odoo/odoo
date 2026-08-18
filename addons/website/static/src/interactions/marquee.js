import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

/**
 * Infinite horizontal marquee: clones a strip of content until it covers the
 * viewport, then lets marquee.css animate it through the `o_marquee_*` classes
 * added here.
 *
 * Subclasses set `classPrefix`, and the DOM follows:
 *   .{prefix} .{prefix}_marquee_container > .{prefix}_marquee_item
 * The prefix stays per snippet, as the markup of `s_announcement_scroll` is
 * saved in databases.
 */
export class Marquee extends Interaction {
    /** @type {string} */
    static classPrefix = "";

    dynamicSelectors = {
        ...this.dynamicSelectors,
        _marqueeContainer: () => this.marqueeContainerEl,
        _marqueeItem: () => this.marqueeItemEl,
    };

    dynamicContent = {
        _root: {
            "t-att-class": () => ({
                o_marquee_ready: this.marqueeReady,
                o_marquee_page_scrolling: this.marqueePageScrolling,
            }),
        },
        // Before `start`, so that the clones inherit it.
        _marqueeItem: {
            "t-att-class": () => ({ o_marquee_item: true }),
        },
        _window: {
            "t-on-resize.passive": this.debounced(this.onResize, 100, {
                leading: true,
                trailing: true,
            }),
            "t-on-scroll.passive": this.throttled(this.onScroll),
        },
        _marqueeContainer: {
            "t-att-style": () => ({
                transform: `translateX(${this.parallaxPosition}%)`,
            }),
        },
    };

    setup() {
        const prefix = this.constructor.classPrefix;
        this.marqueeContainerEl = this.el.querySelector(`.${prefix}_marquee_container`);
        this.marqueeItemEl = this.el.querySelector(`.${prefix}_marquee_item`);
        this.setParallaxPosition();
    }

    start() {
        this.updateMarqueeLayout();
        // Start animation only after layout is computed so the first item and
        // its clones stay aligned.
        this.marqueeReady = true;
        this.updateContent();
    }

    destroy() {
        this.undoMarqueeLayout();
    }

    onResize() {
        this.marqueeReady = false;
        this.updateContent();

        this.updateMarqueeLayout();
        this.marqueeReady = true;
    }

    onScroll() {
        // Needed even without parallax: while the page is scrolling, hovering
        // the element should not trigger the hover effect.
        this.marqueePageScrolling = true;
        window.clearTimeout(this.scrollingTimeout);
        this.scrollingTimeout = this.waitForTimeout(() => {
            this.marqueePageScrolling = false;
        }, 200);

        this.setParallaxPosition();
    }

    /**
     * Sets the parallax position, or the static one without parallax.
     */
    setParallaxPosition() {
        const MIN_LEFT_SHIFT = 50;
        const prefix = this.constructor.classPrefix;

        if (
            !this.el.classList.contains(`${prefix}_parallax`) ||
            window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ) {
            this.parallaxPosition = -MIN_LEFT_SHIFT;
            return;
        }

        // One viewport worth of scroll (window.innerHeight) equals 50% parallax
        // movement.
        const PARALLAX_AMOUNT = 50;
        const rect = this.el.getBoundingClientRect();
        const startScroll = window.scrollY + rect.top - window.innerHeight;
        const endScroll = window.scrollY + rect.bottom;
        const progress = Math.min(
            Math.max((window.scrollY - startScroll) / (endScroll - startScroll), 0),
            1
        );
        if (this.el.classList.contains(`${prefix}_direction_right`)) {
            this.parallaxPosition = -MIN_LEFT_SHIFT - PARALLAX_AMOUNT + progress * PARALLAX_AMOUNT;
        } else {
            this.parallaxPosition = -MIN_LEFT_SHIFT - progress * PARALLAX_AMOUNT;
        }
    }

    /**
     * Undo everything done by previous @see updateMarqueeLayout calls.
     */
    undoMarqueeLayout() {
        while (this.marqueeContainerEl.children.length > 1) {
            this.marqueeContainerEl.lastChild.remove();
        }
        this.marqueeContainerEl.style.removeProperty("--marquee-item-size");
    }

    /**
     * Updates the marquee layout by calculating the items per container and
     * cloning items as needed.
     */
    updateMarqueeLayout() {
        // First, so that the early returns below leave no outdated clone nor
        // `--marquee-item-size` behind.
        this.undoMarqueeLayout();

        const marqueeItemElWidth = this.marqueeItemEl.offsetWidth;
        if (!marqueeItemElWidth) {
            return;
        }
        const itemsPerContainer = Math.ceil(
            this.marqueeContainerEl.offsetWidth / marqueeItemElWidth
        );
        if (itemsPerContainer > 100) {
            return;
        }

        this.marqueeContainerEl.style.setProperty("--marquee-item-size", marqueeItemElWidth);

        // * 2 to have 200% of the container width,
        // + 1 for the reverse animation (see marquee.css)
        const cloneCount = itemsPerContainer * 2 + 1;
        for (let i = 0; i < cloneCount; i++) {
            const cloneEl = this.marqueeItemEl.cloneNode(true);
            cloneEl.classList.add("o_marquee_item_clone");
            this.prepareClone(cloneEl);
            this.marqueeContainerEl.appendChild(cloneEl);
        }
    }

    /**
     * Adapts a clone before it is inserted. Clones are decorative duplicates:
     * they are neither editable, selectable nor exposed to assistive
     * technologies. Subclasses extending this must call `super`.
     *
     * @param {HTMLElement} cloneEl
     */
    prepareClone(cloneEl) {
        cloneEl.classList.add("o_not_editable", "o_snippet_not_selectable");
        cloneEl.setAttribute("aria-hidden", "true");
    }
}

registry.category("public.interactions.edit").add("website.marquee", {
    Interaction: Marquee,
    isAbstract: true,
});
