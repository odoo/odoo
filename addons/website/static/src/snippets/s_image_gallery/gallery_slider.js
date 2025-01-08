import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { isVisible } from "@html_editor/utils/dom_info";


export class GallerySlider extends Interaction {
    static selector = ".o_slideshow";

    setup() {
        this.carouselEl = this.el.classList.contains("carousel") ? this.el : this.el.querySelector(".carousel");
        this.indicatorEl = this.carouselEl?.querySelector(".carousel-indicators");
        if (this.indicatorEl) {
            this.prevEl = this.indicatorEl.querySelector("li.o_indicators_left");
            this.nextEl = this.indicatorEl.querySelector("li.o_indicators_right");
            if (this.prevEl) {
                this.prevEl.style.visibility = ""; // force visibility as some databases have it hidden
            }
            if (this.nextEl) {
                this.nextEl.style.visibility = "";
            }
            this.liEls = this.indicatorEl.querySelectorAll("li[data-bs-slide-to]");
            let indicatorWidth = this.indicatorEl.getBoundingClientRect().width;
            if (indicatorWidth === 0) {
                // An ancestor may be hidden so we try to find it and make it
                // visible just to take the correct width.
                let indicatorParentEl = this.indicatorEl.parentElement;
                while (indicatorParentEl) {
                    if (!isVisible(indicatorParentEl)) {
                        if (!indicatorParentEl.style.display) {
                            indicatorParentEl.style.display = "block";
                            indicatorWidth = this.indicatorEl.getBoundingClientRect().width;
                            indicatorParentEl.style.display = "";
                        }
                        break;
                    }
                    indicatorParentEl = indicatorParentEl.parentElement;
                }
            }
            this.nbPerPage = Math.floor(indicatorWidth / (this.liEls.length > 0 ? this.liEls[0].getBoundingClientRect().width : undefined)) - 3; // - navigator - 1 to leave some space
            this.realNbPerPage = this.nbPerPage || 1;
            this.nbPages = Math.ceil(this.liEls.length / this.realNbPerPage);
        }
        this.update();
    }

    start() {
        if (this.carouselEl) {
            this.addListener(this.carouselEl, "slide.bs.carousel", this.slide);
            this.addListener(this.carouselEl, "slid.bs.carousel", this.update);
        }
        if (this.indicatorEl) {
            this.addListener(this.indicatorEl, "click", this.clickIndicator);// Delegate on "> li:not([data-bs-slide-to])"
        }
    }

    slide(ev) {
        if (!this.carouselEl || !this.liEls) {
            return;
        }
        this.waitForTimeout(() => {
            const itemEl = this.carouselEl.querySelector(".carousel-inner .carousel-item-prev, .carousel-inner .carousel-item-next");
            if (!itemEl) {
                return;
            }
            const index = [...itemEl.parentElement.children].indexOf(itemEl);
            for (const liEl of this.liEls) {
                liEl.classList.remove("active");
            }
            const selectedLiEl = [...this.liEls].find(el => el.dataset.bsSlideTo === `${index}`);
            selectedLiEl?.classList.add("active");
        }, 0);
    }
    clickIndicator(ev) {
        // Delegate from this.indicatorEl.
        const dispatchedEl = ev.target.closest("li:not([data-bs-slide-to])");
        if (!dispatchedEl || dispatchedEl.parentElement !== this.indicatorEl) {
            return;
        }
        this.page += dispatchedEl.classList.contains("o_indicators_left") ? -1 : 1;
        this.page = Math.max(0, Math.min(this.nbPages - 1, this.page)); // should not be necessary
        window.Carousel.getOrCreateInstance(this.carouselEl).to(this.page * this.realNbPerPage);
        // We dont use hide() before the slide animation in the editor because there is a traceback
        // TO DO: fix this traceback
        if (!this.editableMode) {
            this.hide();
        }
    }
    hide() {
        for (let i = 0; i < this.liEls?.length; i++) {
            this.liEls[i].classList.toggle("d-none", i < this.page * this.nbPerPage || i >= (this.page + 1) * this.nbPerPage);
        }
        if (this.prevEl) {
            if (this.page <= 0) {
                this.prevEl.remove();
            } else {
                this.prevEl.classList.remove("d-none");
                this.indicatorEl.insertAdjacentElement("afterbegin", this.prevEl);
            }
        }
        if (this.nextEl) {
            if (this.page >= this.nbPages - 1) {
                this.nextEl.remove();
            } else {
                this.nextEl.classList.remove("d-none");
                this.indicatorEl.appendChild(this.nextEl);
            }
        }
    }
    update() {
        if (this.liEls) {
            const active = [...this.liEls].filter((el) => el.classList.contains("active"));
            const index = active.length ? [...this.liEls].indexOf(active) : 0;
            this.page = Math.floor(index / this.realNbPerPage);
        }
        this.hide();
    }
    destroy() {
        if (this.prevEl) {
            this.indicatorEl.prepend(this.prevEl);
        }
        if (this.nextEl) {
            this.indicatorEl.append(this.nextEl);
        }
    }
}

registry.category("public.interactions").add("website.gallery_slider", GallerySlider);

registry
    .category("public.interactions.edit")
    .add("website.gallery_slider", {
        Interaction: GallerySlider,
    });
