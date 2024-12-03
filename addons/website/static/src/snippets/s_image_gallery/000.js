import { registry } from "@web/core/registry";
import { Interaction } from "@website/core/interaction";
import { uniqueId } from "@web/core/utils/functions";
import { renderToElement } from "@web/core/utils/render";
import { isVisible } from "@html_editor/utils/dom_info";


export class GalleryWidget extends Interaction {
    static selector = ".s_image_gallery:not(.o_slideshow)";
    dynamicContent = {
        "img": {
            "t-on-click": this.clickImg,
        },
    };

    setup() {
        this.modalEl = null;
        this.originalSources = [...this.el.querySelectorAll("img")].map(img => img.getAttribute("src"));
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when an image is clicked. Opens a dialog to browse all the images
     * with a bigger size.
     *
     * @param {Event} ev
     */
    clickImg(ev) {
        const clickedEl = ev.currentTarget;
        if (this.modalEl || clickedEl.matches("a > img")) {
            return;
        }

        let imageEls = this.el.querySelectorAll("img");
        const currentImageEl = clickedEl.closest("img");
        const currentImageIndex = [...imageEls].indexOf(currentImageEl);
        // We need to reset the images to their original source because it might
        // have been changed by a mouse event (e.g. "hover effect" animation).
        imageEls = [...imageEls].map((el, i) => {
            const cloneEl = el.cloneNode(true);
            cloneEl.src = this.originalSources[i];
            return cloneEl;
        });

        const size = 0.8;
        const dimensions = {
            min_width: Math.round(window.innerWidth * size * 0.9),
            min_height: Math.round(window.innerHeight * size),
            max_width: Math.round(window.innerWidth * size * 0.9),
            max_height: Math.round(window.innerHeight * size),
            width: Math.round(window.innerWidth * size * 0.9),
            height: Math.round(window.innerHeight * size)
        };

        const milliseconds = this.el.dataset.interval || false;
        const lightboxTemplate = this.el.dataset.vcss === "002" ?
            "website.gallery.s_image_gallery_mirror.lightbox" :
            "website.gallery.slideshow.lightbox";
        this.modalEl = renderToElement(lightboxTemplate, {
            images: imageEls,
            index: currentImageIndex,
            dim: dimensions,
            interval: milliseconds || 0,
            ride: !milliseconds ? "false" : "carousel",
            id: uniqueId("slideshow_"),
        });
        this.__onModalKeydown = this._onModalKeydown.bind(this);
        this.modalEl.addEventListener("hidden.bs.modal", () => {
            this.modalEl.classList.add("d-none");
            for (const backdropEl of this.modalEl.querySelectorAll(".modal-backdrop")) {
                backdropEl.remove(); // bootstrap leaves a modal-backdrop
            }
            const slideshowEl = this.modalEl.querySelector(".modal-body.o_slideshow");
            this.services.website_core.stopInteractions(slideshowEl);
            this.modalEl.removeEventListener("keydown", this.__onModalKeydown);
            this.modalEl.remove();
            this.modalEl = undefined;
        });
        this.modalEl.addEventListener("shown.bs.modal", () => {
            const slideshowEl = this.modalEl.querySelector(".modal-body.o_slideshow");
            this.services.website_core.startInteractions(slideshowEl);
            this.modalEl.addEventListener("keydown", this.__onModalKeydown);
        }, { once: true });
        document.body.append(this.modalEl);
        const modalBS = new Modal(this.modalEl, {keyboard: true, backdrop: true});
        modalBS.show();
    }
    _onModalKeydown(ev) {
        if (ev.key === "ArrowLeft" || ev.key === "ArrowRight") {
            const side = ev.key === "ArrowLeft" ? "prev" : "next";
            this.modalEl.querySelector(`.carousel-control-${side}`).click();
        }
        if (ev.key === "Escape") {
            // If the user is connected as an editor, prevent the backend header
            // from collapsing.
            ev.stopPropagation();
        }
    }
}

export class GallerySliderWidget extends Interaction {
    static selector = ".o_slideshow";
    // TODO Support edit-mode enabled.
    static disabledInEditableMode = false;

    setup() {
        this.carouselEl = this.el.classList.contains("carousel") ? this.el : this.el.querySelector(".carousel");
        this.indicatorEl = this.carouselEl.querySelector(".carousel-indicators");
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

        this.update();
    }

    start() {
        this.addListener(this.carouselEl, "slide.bs.carousel", this.slide);
        this.addListener(this.carouselEl, "slid.bs.carousel", this.update);
        this.addListener(this.indicatorEl, "click", this.clickIndicator);// Delegate on "> li:not([data-bs-slide-to])"
    }

    slide(ev) {
        this.waitForTimeout(() => {
            const itemEl = this.carouselEl.querySelector(".carousel-inner .carousel-item-prev, .carousel-inner .carousel-item-next");
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
        Carousel.getOrCreateInstance(this.carouselEl).to(this.page * this.realNbPerPage);
        // We dont use hide() before the slide animation in the editor because there is a traceback
        // TO DO: fix this traceback
        if (!this.editableMode) {
            this.hide();
        }
    }
    hide() {
        for (let i = 0; i < this.liEls.length; i++) {
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
        const active = [...this.liEls].filter((el) => el.classList.contains("active"));
        const index = active.length ? [...this.liEls].indexOf(active) : 0;
        this.page = Math.floor(index / this.realNbPerPage);
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

registry.category("website.active_elements").add("website.gallery", GalleryWidget);
registry.category("website.active_elements").add("website.gallery_slider", GallerySliderWidget);

