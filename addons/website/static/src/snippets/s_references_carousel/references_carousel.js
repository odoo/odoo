import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class ReferencesCarousel extends Interaction {
    static selector = ".s_references_carousel";

    dynamicContent = {
        _root: {
            "t-att-class": () => ({
                s_references_carousel_ready: this.carouselReady,
                s_references_carousel_page_scrolling: this.pageScrolling,
            }),
        },
        _window: {
            "t-on-resize": this.debounced(this.onResize, 100, { leading: true, trailing: true }),
            "t-on-scroll": this.throttled(this.onScroll),
        },
    };

    setup() {
        this.containerEl = this.el.querySelector(".s_references_carousel_container");
        this.groupEl = this.el.querySelector(".s_references_carousel_group");
    }

    start() {
        this.updateCarouselLayout();
        this.carouselReady = true;
        this.updateContent();
    }

    destroy() {
        this.undoCarouselLayout();
    }

    onResize() {
        this.carouselReady = false;
        this.updateContent();

        this.updateCarouselLayout();
        this.carouselReady = true;
    }

    onScroll() {
        // Prevent hover effects while scrolling the page.
        this.pageScrolling = true;
        window.clearTimeout(this.scrollingTimeout);
        this.scrollingTimeout = this.waitForTimeout(() => {
            this.pageScrolling = false;
        }, 200);
    }

    undoCarouselLayout() {
        for (const clone of this.containerEl.querySelectorAll(".s_references_carousel_group_clone")) {
            clone.remove();
        }
        this.containerEl.style.removeProperty("--carousel-group-size");
    }

    updateCarouselLayout() {
        const groupWidth = this.groupEl.offsetWidth;
        const containerWidth = this.containerEl.offsetWidth;
        const groupsPerContainer = Math.ceil(containerWidth / groupWidth);
        if (groupsPerContainer > 100) {
            return;
        }

        this.undoCarouselLayout();

        this.containerEl.style.setProperty("--carousel-group-size", groupWidth);

        // Need enough clones so that when the first group scrolls out,
        // the next fills the container seamlessly. +1 for safety.
        const cloneCount = groupsPerContainer + 1;
        for (let i = 0; i < cloneCount; i++) {
            const cloneEl = this.groupEl.cloneNode(true);
            cloneEl.classList.add("s_references_carousel_group_clone");
            this.containerEl.appendChild(cloneEl);
        }
    }
}

registry.category("public.interactions").add("website.references_carousel", ReferencesCarousel);
