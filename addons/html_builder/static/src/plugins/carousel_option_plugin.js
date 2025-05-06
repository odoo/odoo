import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { CarouselItemHeaderMiddleButtons } from "./carousel_item_header_buttons";
import { renderToElement } from "@web/core/utils/render";

export class CarouselOptionPlugin extends Plugin {
    static id = "carouselOption";
    static dependencies = ["clone", "history", "remove", "builder-options"];
    static shared = ["slide", "addSlide", "removeSlide"];

    resources = {
        builder_options: [
            {
                template: "html_builder.CarouselOption",
                selector: "section",
                exclude: ".s_carousel_intro_wrapper, .s_carousel_cards_wrapper",
                applyTo: ":scope > .carousel",
            },
            {
                template: "html_builder.CarouselBottomControllersOption",
                selector: "section",
                applyTo: ".s_carousel_intro",
            },
            {
                template: "html_builder.CarouselCardsOption",
                selector: "section",
                applyTo: ".s_carousel_cards",
            },
        ],
        builder_header_middle_buttons: {
            Component: CarouselItemHeaderMiddleButtons,
            selector:
                ".s_carousel .carousel-item, .s_quotes_carousel .carousel-item, .s_carousel_intro .carousel-item, .s_carousel_cards .carousel-item",
            props: {
                slideCarousel: (direction, editingElement) =>
                    this.slideCarousel(editingElement.closest(".carousel"), direction),
                addSlide: (editingElement) => this.addSlide(editingElement.closest(".carousel")),
                removeSlide: (editingElement) =>
                    this.removeSlide(editingElement.closest(".carousel")),
            },
        },
        container_title: {
            selector:
                ".s_carousel .carousel-item, .s_quotes_carousel .carousel-item, .s_carousel_intro .carousel-item, .s_carousel_cards .carousel-item",
            getTitleExtraInfo: (editingElement) => this.getTitleExtraInfo(editingElement),
        },
        builder_actions: this.getActions(),
        on_cloned_handlers: this.onCloned.bind(this),
        on_will_clone_handlers: this.onWillClone.bind(this),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
        normalize_handlers: this.normalize.bind(this),
        on_reorder_items_handlers: this.reorderCarouselItems.bind(this),
        before_save_handlers: () => {
            const proms = [];
            for (const carouselEl of this.editable.querySelectorAll(".carousel")) {
                const firstItem = carouselEl.querySelector(".carousel-item");
                if (firstItem.classList.contains("active")) {
                    continue;
                }
                proms.push(this.slide(carouselEl, 0));
            }
            return Promise.all(proms);
        },
    };

    getActions() {
        return {
            addSlide: {
                preview: false,
                apply: async ({ editingElement }) => this.addSlide(editingElement),
            },
            slideCarousel: {
                preview: false,
                apply: async ({ editingElement, direction: direction }) =>
                    this.slideCarousel(editingElement, direction),
            },
            toggleControllers: {
                apply: ({ editingElement }) => {
                    const carouselEl = editingElement.closest(".carousel");
                    const indicatorsWrapEl = carouselEl.querySelector(".carousel-indicators");
                    const areControllersHidden =
                        carouselEl.classList.contains("s_carousel_arrows_hidden") &&
                        indicatorsWrapEl.classList.contains("s_carousel_indicators_hidden");
                    carouselEl.classList.toggle(
                        "s_carousel_controllers_hidden",
                        areControllersHidden
                    );
                },
            },
            toggleCardImg: {
                apply: ({ editingElement }) => this.toggleCardImg(editingElement),
                clean: ({ editingElement: el }) => {
                    const carouselEl = el.closest(".carousel");
                    carouselEl.querySelectorAll("figure").forEach((el) => el.remove());
                },
                isApplied: ({ editingElement }) => {
                    const carouselEl = editingElement.closest(".carousel");
                    const cardImgEl = carouselEl.querySelector(".o_card_img_wrapper");
                    return !!cardImgEl;
                },
            },
        };
    }

    toggleCardImg(editingElement) {
        const carouselEl = editingElement.closest(".carousel");
        const cardEls = carouselEl.querySelectorAll(".card");
        for (const cardEl of cardEls) {
            const imageWrapperEl = renderToElement("html_builder.s_carousel_cards.imageWrapper");
            cardEl.insertAdjacentElement("afterbegin", imageWrapperEl);
        }
    }

    getTitleExtraInfo(editingElement) {
        const itemsEls = [...editingElement.parentElement.children];
        const activeIndex = itemsEls.indexOf(editingElement);

        const updatedText = ` (${activeIndex + 1}/${itemsEls.length})`;
        return updatedText;
    }

    async addSlide(editingElement) {
        const activeCarouselItem = editingElement.querySelector(".carousel-item.active");
        this.dependencies.clone.cloneElement(activeCarouselItem);

        await this.slide(editingElement, "next");
        this.dependencies.history.addStep();
        this.dependencies["builder-options"].updateContainers(
            editingElement.querySelector(".carousel-item.active")
        );
    }

    async removeSlide(editingCarouselElement) {
        const toRemoveCarouselItemEl =
            editingCarouselElement.querySelector(".carousel-item.active");
        const toRemoveIndicatorEl = editingCarouselElement.querySelector(
            ".carousel-indicators > .active"
        );
        const itemsEls = [...editingCarouselElement.querySelectorAll(".carousel-item")];

        if (itemsEls.length > 1) {
            // Slide to the previous item
            await this.slide(editingCarouselElement, "prev");

            // Remove the carousel item and the indicator
            this.dependencies.remove.removeElement(toRemoveCarouselItemEl);
            this.dependencies.remove.removeElement(toRemoveIndicatorEl);

            this.dependencies.history.addStep();
            this.dependencies["builder-options"].updateContainers(
                editingCarouselElement.querySelector(".carousel-item.active")
            );
        }
    }

    async slideCarousel(editingElement, direction) {
        await this.slide(editingElement, direction);
        this.dependencies.history.addStep();
        this.dependencies["builder-options"].updateContainers(
            editingElement.querySelector(".carousel-item.active")
        );
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
    slide(editingElement, direction) {
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
        if (originalEl.matches(".carousel-item")) {
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
                ".s_carousel_wrapper, .s_carousel_intro_wrapper, .s_carousel_cards_wrapper"
            )
        ) {
            this.assignUniqueID(cloneEl);
        }
        if (cloneEl.matches(".carousel-item")) {
            // Need to remove editor data from the clone so it gets its own.
            cloneEl.classList.remove("active");
        }
    }

    onSnippetDropped({ snippetEl }) {
        if (
            snippetEl.matches(
                ".s_carousel_wrapper, .s_carousel_intro_wrapper, .s_carousel_cards_wrapper"
            )
        ) {
            this.assignUniqueID(snippetEl);
        }
    }

    assignUniqueID(editingElement) {
        const id = "myCarousel" + Date.now();
        editingElement.querySelector(".carousel").setAttribute("id", id);
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
        const carousel = root.closest(".carousel");
        const allCarousels = [...root.querySelectorAll(".carousel")];
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
     * @todo: find the root cause and remove this fix.
     */
    fixWrongHistoryOnCarousels(carousels) {
        for (const carousel of carousels) {
            const carouselItems = carousel.querySelectorAll(".carousel-item");
            const activeCarouselItems = carousel.querySelectorAll(".carousel-item.active");
            if (!activeCarouselItems.length) {
                carouselItems[0].classList.add("active");
                const indicatorsEl = carousel.querySelector(".carousel-indicators");
                const activeIndicatorEl = [...indicatorsEl.children][0];
                activeIndicatorEl.classList.add("active");
                activeIndicatorEl.setAttribute("aria-current", "true");
            }
        }
    }

    reorderCarouselItems({ elementToReorder, position, optionName }) {
        if (optionName === "Carousel") {
            const editingCarouselElement = elementToReorder.closest(".carousel");
            const itemsEls = [...editingCarouselElement.querySelectorAll(".carousel-item")];

            // reorder carousel items
            const oldPosition = itemsEls.indexOf(elementToReorder);
            if (oldPosition === 0 && position === "prev") {
                position = "last";
            } else if (oldPosition === itemsEls.length - 1 && position === "next") {
                position = "first";
            }
            itemsEls.splice(oldPosition, 1);
            switch (position) {
                case "first":
                    itemsEls.unshift(elementToReorder);
                    break;
                case "prev":
                    itemsEls.splice(Math.max(oldPosition - 1, 0), 0, elementToReorder);
                    break;
                case "next":
                    itemsEls.splice(oldPosition + 1, 0, elementToReorder);
                    break;
                case "last":
                    itemsEls.push(elementToReorder);
                    break;
            }

            // replace the carousel-inner element by one with reordered carousel items
            const carouselInnerEl = editingCarouselElement.querySelector(".carousel-inner");
            const newCarouselInnerEl = document.createElement("div");
            newCarouselInnerEl.classList.add("carousel-inner");
            newCarouselInnerEl.append(...itemsEls);
            carouselInnerEl.replaceWith(newCarouselInnerEl);

            // slide to the reordered target carousel item and update indicators
            const newItemPosition = itemsEls.indexOf(elementToReorder);
            editingCarouselElement.classList.remove("slide");
            const carouselInstance = window.Carousel.getOrCreateInstance(editingCarouselElement, {
                ride: false,
                pause: true,
            });
            carouselInstance.to(newItemPosition);
            const indicatorEls = editingCarouselElement.querySelectorAll(
                ".carousel-indicators > *"
            );
            indicatorEls.forEach((indicatorEl, i) => {
                indicatorEl.classList.toggle("active", i === newItemPosition);
            });
            editingCarouselElement.classList.add("slide");
            // Prevent the carousel from automatically sliding afterwards.
            carouselInstance["pause"]();

            const activeImageEl = editingCarouselElement.querySelector(".carousel-item.active img");
            this.dependencies.history.addStep();
            this.dependencies["builder-options"].updateContainers(activeImageEl);
        }
    }
}

registry.category("website-plugins").add(CarouselOptionPlugin.id, CarouselOptionPlugin);
