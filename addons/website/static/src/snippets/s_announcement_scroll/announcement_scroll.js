import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";


export class AnnouncementScroll extends Interaction {
    static selector = ".s_announcement_scroll";

    dynamicContent = {
        _window: {
            "t-on-resize": this.debounced(this.onResize, 100),
            "t-on-scroll": this.throttled(this.onScroll),
        },
        ".s_announcement_scroll_marquee_container": {
            "t-att-style": () => ({
                "transform": `translateX(${this.parallaxPosition}%)`
            }),
        },
    }

    setup() {
        this.marqueeContainerEl = this.el.querySelector('.s_announcement_scroll_marquee_container');
        this.marqueeItemEl = this.el.querySelector('.s_announcement_scroll_marquee_item');
        this.marqueeContainerElWidth = this.marqueeContainerEl.offsetWidth;
        this.marqueeItemElWidth = 0;
        this.itemsPerContainer = 0;
        this.scrollText = this.el.dataset.scrollcontent;
        this.windowHeight = window.innerHeight;
        this.parallaxPosition = -50;
        this.lastScrollY = window.scrollY;
        this.scrollDelta = 0;
        this.scrollTimeout = null;
    }

    start() {
        this.el.style.setProperty('--marquee-item-font-size', `${this.el.dataset.marqueeFontSize}`);
        this.marqueeItemEl.textContent = _t(this.scrollText);
        this.marqueeItemElWidth = this.marqueeItemEl.offsetWidth;
        this.marqueeContainerEl.style.setProperty("--marquee-item-size", this.marqueeItemElWidth);
        this.updateMarqueeLayout();
        this.isElementInViewport() ?
            this.el.classList.add('s_announcement_scroll_in_viewport') :
            this.el.classList.remove('s_announcement_scroll_in_viewport');
        // The animation should start when the computation is done,
        // else the first element will be already further than its clones
        this.el.classList.add('s_announcement_scroll_ready');
    }

    /**
     * Handles window resize events by recalculating dimensions and updating the
     * marquee layout.
     */
    onResize() {
        this.el.classList.remove('s_announcement_scroll_ready');
        this.marqueeItemElWidth = this.marqueeItemEl.offsetWidth;
        this.marqueeContainerElWidth = this.marqueeContainerEl.offsetWidth;
        this.windowHeight = window.innerHeight;
        this.updateMarqueeLayout();
        this.el.classList.add('s_announcement_scroll_ready');
    }

    /**
     * Handles scroll events for parallax effect when enabled.
     */
    onScroll() {
        if (!this.el.classList.contains('s_announcement_scroll_parallax')) {
            return;
        }
        if (this.isElementInViewport()) {
            this.el.classList.add('s_announcement_scroll_in_viewport');
            this.el.classList.add('s_announcement_scroll_page_scrolling');
            clearTimeout(this.scrollTimeout);
            this.scrollTimeout = setTimeout(() => {
                this.el.classList.remove('s_announcement_scroll_page_scrolling');
            }, 200);
            this.scrollDelta = window.scrollY - this.lastScrollY;
            // One viewport worth of scroll (this.windowHeight) equals 50% parallax movement
            this.el.classList.contains('s_announcement_scroll_direction_right') ?
                this.parallaxPosition += (this.scrollDelta / this.windowHeight) * 50 :
                this.parallaxPosition -= (this.scrollDelta / this.windowHeight) * 50;
            this.lastScrollY = window.scrollY;
        } else {
            // Reset parallax position when element is not in viewport
            this.el.classList.remove('s_announcement_scroll_in_viewport');
            this.parallaxPosition = -50;
        }
    }

    destroy() {
        if (this.scrollTimeout) {
            clearTimeout(this.scrollTimeout);
            this.scrollTimeout = null;
        }
        this.el.classList.remove(
            's_announcement_scroll_ready',
            's_announcement_scroll_page_scrolling',
            's_announcement_scroll_in_viewport'
        );
        this.marqueeContainerEl.querySelectorAll('.s_announcement_scroll_marquee_item_clone').forEach(el => {
            el.remove();
        });
        this.marqueeContainerEl.style.removeProperty('--marquee-item-size');
    }

    /**
     * Updates the marquee layout by calculating the items per container and
     * cloning items as needed.
     */
    updateMarqueeLayout() {
        // Remove existing clones first
        this.marqueeContainerEl.querySelectorAll('.s_announcement_scroll_marquee_item_clone').forEach(el => {
            el.remove();
        });
        this.itemsPerContainer = Math.ceil(this.marqueeContainerElWidth / this.marqueeItemElWidth);
        if (this.el.dataset.scrollcontent) {
            // * 2 to have 200% of the container width,
            // + 1 for the reverse animation (see o-marquee-scroll-left-infinite in 000.scss)
            const cloneCount = this.itemsPerContainer * 2 + 1;
            for (let i = 0; i < cloneCount; i++) {
                const clone = this.marqueeItemEl.cloneNode(true);
                clone.classList.add('s_announcement_scroll_marquee_item_clone');
                this.marqueeContainerEl.appendChild(clone);
            }
        }
    }

    /**
     * Checks if the marquee container is currently visible in the viewport.
     * @returns {boolean}
     */
    isElementInViewport() {
        const rect = this.marqueeContainerEl.getBoundingClientRect();
        return (
            rect.top < window.innerHeight && rect.bottom > 0 &&
            rect.left < window.innerWidth && rect.right > 0
        );
    }
}

registry
    .category("public.interactions")
    .add("website.announcement_scroll", AnnouncementScroll);

registry
    .category("public.interactions.edit")
    .add("website.announcement_scroll", {
        Interaction: AnnouncementScroll,
    });
