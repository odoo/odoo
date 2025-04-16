import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class CarouselOptionPlugin extends Plugin {
    static id = "carouselOption";
    static dependencies = ["clone"];

    resources = {
        builder_options: [
            {
                template: "html_builder.CarouselOption",
                selector: "section",
                exclude: ".s_carousel_intro_wrapper, .s_carousel_cards_wrapper",
                applyTo: ":scope > .carousel",
            },
        ],
        builder_actions: this.getActions(),
        on_cloned_handlers: this.onCloned.bind(this),
        on_will_clone_handlers: this.onWillClone.bind(this),
        on_add_element_handlers: this.onAddElement.bind(this),
        normalize_handlers: this.normalize.bind(this),
    };

    getActions() {
        return {
            addSlide: {
                load: async ({ editingElement }) => this.addSlide(editingElement),
                apply: () => {},
            },
            slideCarousel: {
                load: async ({ editingElement, direction: direction }) =>
                    this.slide(direction, editingElement),
                apply: () => {},
            },
        };
    }

    async addSlide(editingElement) {
        const activeCarouselItem = editingElement.querySelector(".carousel-item.active");
        this.dependencies.clone.cloneElement(activeCarouselItem);

        await this.slide("next", editingElement);
    }

    /**
     * Slides the carousel in the given direction.
     *
     * @param {String|Number} direction the direction in which to slide:
     *     - "prev": the previous slide;
     *     - "next": the next slide;
     *     - number: a slide number.
     * @param {Element} editingElement the carousel element.
     * @returns {Promise}
     */
    slide(direction, editingElement) {
        editingElement.addEventListener("slide.bs.carousel", () => {
            this.slideTimestamp = window.performance.now();
        });

        return new Promise((resolve) => {
            editingElement.addEventListener("slid.bs.carousel", () => {
                // slid.bs.carousel is most of the time fired too soon by bootstrap
                // since it emulates the transitionEnd with a setTimeout. We wait
                // here an extra 20% of the time before retargeting edition, which
                // should be enough...
                const slideDuration = window.performance.now() - this.slideTimestamp;
                setTimeout(() => {
                    // Setting the active indicator manually, as Bootstrap could
                    // not do it because the `data-bs-slide-to` attribute is not
                    // here in edit mode anymore.
                    const activeSlide = editingElement.querySelector(".carousel-item.active");
                    const indicatorsEl = editingElement.querySelector(".carousel-indicators");
                    const activeIndex = [...activeSlide.parentElement.children].indexOf(
                        activeSlide
                    );
                    const activeIndicatorEl = [...indicatorsEl.children][activeIndex];
                    activeIndicatorEl.classList.add("active");
                    activeIndicatorEl.setAttribute("aria-current", "true");

                    resolve();
                }, 0.2 * slideDuration);
            });

            const carouselInstance = window.Carousel.getOrCreateInstance(editingElement, {
                ride: false,
                pause: true,
            });
            if (typeof direction === "number") {
                carouselInstance.to(direction);
            } else {
                carouselInstance[direction]();
            }
        });
    }

    onWillClone({ originalEl }) {
        if (
            originalEl.matches(
                ".s_carousel_wrapper:not(.s_carousel_intro_wrapper, .s_carousel_cards_wrapper) .carousel-item"
            )
        ) {
            const editingCarousel = originalEl.closest(".carousel");

            const indicatorsEl = editingCarousel.querySelector(".carousel-indicators");
            this.controlEls = editingCarousel.querySelectorAll(
                ".carousel-control-prev, .carousel-control-next, .carousel-indicators"
            );
            this.controlEls.forEach((control) => {
                control.classList.remove("d-none");
            });

            const newIndicatorEl = this.document.createElement("button");
            newIndicatorEl.setAttribute("data-bs-target", "#" + editingCarousel.id);
            newIndicatorEl.setAttribute("aria-label", _t("Carousel indicator"));
            indicatorsEl.appendChild(newIndicatorEl);
        }
    }

    onCloned({ cloneEl }) {
        if (
            cloneEl.matches(
                ".s_carousel_wrapper:not(.s_carousel_intro_wrapper, .s_carousel_cards_wrapper)"
            )
        ) {
            this.assignUniqueID(cloneEl);
        }
        if (
            cloneEl.matches(
                ".s_carousel_wrapper:not(.s_carousel_intro_wrapper, .s_carousel_cards_wrapper) .carousel-item"
            )
        ) {
            // Need to remove editor data from the clone so it gets its own.
            cloneEl.classList.remove("active");
        }
    }

    onAddElement({ elementToAdd }) {
        if (elementToAdd.matches(".s_carousel_wrapper")) {
            this.assignUniqueID(elementToAdd);
        }
    }

    assignUniqueID(editingElement) {
        const id = "myCarousel" + Date.now();
        editingElement.querySelector(".s_carousel").setAttribute("id", id);
        editingElement.querySelectorAll("[data-bs-target]").forEach((el) => {
            el.setAttribute("data-bs-target", "#" + id);
        });
        editingElement.querySelectorAll("[data-bs-slide], [data-bs-slide-to]").forEach((el) => {
            if (el.hasAttribute("data-bs-target")) {
                el.setAttribute("data-bs-target", "#" + id);
            } else if (el.hasAttribute("href")) {
                el.setAttribute("href", "#" + id);
            }
        });
    }
    normalize(root) {
        const carousel = root.closest(".s_carousel");
        const allCarousels = root.querySelectorAll(".s_carousel");
        if (carousel) {
            allCarousels.push(carousel);
        }
        this.fixWrongHistoryOnCarousels(allCarousels);
    }
    /**
     * This fix is exists to workaround a bug:
     * - add slide
     * - undo
     * - redo
     * => the active class of the carousel item and therefore it looks like the carrousel is empty.
     *
     * Todo: find the root cause and remove this fix.
     */
    fixWrongHistoryOnCarousels(carousels) {
        for (const carousel of carousels) {
            const carouselItems = carousel.querySelectorAll(".carousel-item");
            const activeCarouselItems = carousel.querySelectorAll(".carousel-item.active");
            if (!activeCarouselItems.length) {
                carouselItems[0].classList.add("active");
                // carouselItems[0].setAttribute("aria-current", "true");
                const indicatorsEl = carousel.querySelector(".carousel-indicators");
                const activeIndicatorEl = [...indicatorsEl.children][0];
                activeIndicatorEl.classList.add("active");
                activeIndicatorEl.setAttribute("aria-current", "true");
            }
        }
    }
}

registry.category("website-plugins").add(CarouselOptionPlugin.id, CarouselOptionPlugin);
