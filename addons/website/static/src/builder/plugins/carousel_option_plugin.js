import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { CarouselItemHeaderMiddleButtons } from "./carousel_item_header_buttons";
import { renderToElement } from "@web/core/utils/render";
import { BuilderAction } from "@html_builder/core/builder_action";
import { withSequence } from "@html_editor/utils/resource";
import { between } from "@html_builder/utils/option_sequence";
import { WEBSITE_BACKGROUND_OPTIONS, BOX_BORDER_SHADOW } from "@website/builder/option_sequence";
import { selectElements } from "@html_editor/utils/dom_traversal";

export const CAROUSEL_CARDS_SEQUENCE = between(WEBSITE_BACKGROUND_OPTIONS, BOX_BORDER_SHADOW);

const carouselWrapperSelector =
    ".s_carousel_wrapper, .s_carousel_intro_wrapper, .s_carousel_cards_wrapper";
const carouselControlsSelector =
    ".carousel-control-prev, .carousel-control-next, .carousel-indicators";

const carouselItemOptionSelector = ".s_carousel .carousel-item, .s_quotes_carousel .carousel-item, .s_carousel_intro .carousel-item, .s_carousel_cards .carousel-item";

export class CarouselOptionPlugin extends Plugin {
    static id = "carouselOption";
    static dependencies = ["clone", "builderOptions", "builderActions"];
    static shared = ["addSlide", "removeSlide", "slideCarousel"];

    resources = {
        builder_options: [
            {
                template: "website.CarouselOption",
                selector: "section",
                exclude:
                    ".s_carousel_intro_wrapper, .s_carousel_cards_wrapper, .s_quotes_carousel_wrapper:has(>.s_quotes_carousel_compact)",
                applyTo: ":scope > .carousel",
            },
            {
                template: "website.CarouselBottomControllersOption",
                selector: "section",
                applyTo: ".s_carousel_intro, .s_quotes_carousel_compact",
            },
            withSequence(CAROUSEL_CARDS_SEQUENCE, {
                template: "website.CarouselCardsOption",
                selector: "section",
                applyTo: ".s_carousel_cards",
            }),
        ],
        builder_header_middle_buttons: {
            Component: CarouselItemHeaderMiddleButtons,
            selector: carouselItemOptionSelector,
            props: {
                addSlide: (editingElement) => this.addSlide(editingElement.closest(".carousel")),
                removeSlide: async (editingElement) => {
                    // Check if the slide is still in the DOM
                    // TODO: find a more general way to handle target element already removed by an option
                    if (editingElement.parentElement) {
                        await this.removeSlide(editingElement.closest(".carousel"));
                    }
                },
                applyAction: this.dependencies.builderActions.applyAction,
            },
        },
        container_title: {
            selector: carouselItemOptionSelector,
            getTitleExtraInfo: (editingElement) => this.getTitleExtraInfo(editingElement),
        },
        builder_actions: {
            AddSlideAction,
            SlideCarouselAction,
            ToggleControllersAction,
            ToggleCardImgAction,
        },
        on_cloned_handlers: this.onCloned.bind(this),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
        get_gallery_items_handlers: this.getGalleryItems.bind(this),
        reorder_items_handlers: this.reorderCarouselItems.bind(this),
        before_save_handlers: this.restoreCarousels.bind(this),
        is_unremovable_selector: carouselItemOptionSelector,
    };

    /**
     * Restores all the carousels so their first slide is the active one.
     */
    restoreCarousels(rootEl = this.editable) {
        // Set the first slide as the active one.
        for (const carouselEl of selectElements(rootEl,".carousel")) {
            carouselEl.querySelectorAll(".carousel-item").forEach((itemEl, i) => {
                itemEl.classList.remove("next", "prev", "left", "right");
                itemEl.classList.toggle("active", i === 0);
            });
            carouselEl.querySelectorAll(".carousel-indicators > *").forEach((indicatorEl, i) => {
                indicatorEl.classList.toggle("active", i === 0);
                indicatorEl.removeAttribute("aria-current");
                if (i === 0) {
                    indicatorEl.setAttribute("aria-current", "true");
                }
            });
        }
    }

    getTitleExtraInfo(editingElement) {
        const itemEls = [...editingElement.parentElement.children];
        const activeIndex = itemEls.indexOf(editingElement);
        // Updates the slide counter.
        const updatedText = ` (${activeIndex + 1}/${itemEls.length})`;
        return updatedText;
    }

    /**
     * Adds a slide.
     *
     * @param {HTMLElement} editingElement the carousel element.
     */
    async addSlide(editingElement) {
        // Clone the active item and remove the "active" class.
        const activeItemEl = editingElement.querySelector(".carousel-item.active");
        const newItemEl = await this.dependencies.clone.cloneElement(activeItemEl, {
            activateClone: false,
        });
        newItemEl.classList.remove("active");

        // Show the controllers (now that there is always more than one item).
        const controlEls = editingElement.querySelectorAll(carouselControlsSelector);
        controlEls.forEach((controlEl) => {
            controlEl.classList.remove("d-none");
        });

        // Add the new indicator.
        const indicatorsEl = editingElement.querySelector(".carousel-indicators");
        const newIndicatorEl = this.document.createElement("button");
        newIndicatorEl.setAttribute("data-bs-target", "#" + editingElement.id);
        newIndicatorEl.setAttribute("aria-label", _t("Carousel indicator"));
        indicatorsEl.appendChild(newIndicatorEl);

        // Slide to the new item.
        await this.slide(editingElement, "next");
    }

    /**
     * Removes the current slide.
     *
     * @param {HTMLElement} editingElement the carousel element.
     */
    async removeSlide(editingElement) {
        const itemEls = [...editingElement.querySelectorAll(".carousel-item")];
        const newLength = itemEls.length - 1;
        if (newLength > 0) {
            const activeItemEl = editingElement.querySelector(".carousel-item.active");
            const activeIndicatorEl = editingElement.querySelector(
                ".carousel-indicators > .active"
            );
            // Slide to the previous item.
            await this.slide(editingElement, "prev");

            // Remove the carousel item and the indicator.
            activeItemEl.remove();
            activeIndicatorEl.remove();

            // Hide the controllers if there is only one slide left.
            const controlEls = editingElement.querySelectorAll(carouselControlsSelector);
            controlEls.forEach((controlEl) =>
                controlEl.classList.toggle("d-none", newLength === 1)
            );
        }
    }

    /**
     * Slides the carousel.
     *
     * @param {HTMLElement} editingElement the carousel element.
     * @param {String} direction "prev" or "next".
     */
    async slideCarousel(editingElement, direction) {
        await this.slide(editingElement, direction);
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
                    const itemEls = editingElement.querySelectorAll(".carousel-item");
                    const activeItemEl = editingElement.querySelector(".carousel-item.active");
                    const activeIndex = [...itemEls].indexOf(activeItemEl);
                    const indicatorEls = editingElement.querySelectorAll(
                        ".carousel-indicators > *"
                    );
                    const activeIndicatorEl = [...indicatorEls][activeIndex];
                    activeIndicatorEl.classList.add("active");
                    activeIndicatorEl.setAttribute("aria-current", "true");

                    // Activate the active item.
                    this.dependencies["builderOptions"].setNextTarget(activeItemEl);

                    resolve();
                }, 0.2 * slideDuration);
            }, { once: true });

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

    onCloned({ cloneEl }) {
        if (cloneEl.matches(carouselWrapperSelector)) {
            this.assignUniqueID(cloneEl);
        }
    }

    onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(carouselWrapperSelector)) {
            this.assignUniqueID(snippetEl);
        }
    }

    /**
     * Creates a unique ID for the carousel and reassign data-attributes that
     * depend on it.
     *
     * @param {HTMLElement} editingElement the carousel element.
     */
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

    /**
     * Gets the carousel items to reorder.
     *
     * @param {HTMLElement} activeItemEl the current active item
     * @param {String} optionName
     * @returns {Array<HTMLElement>}
     */
    getGalleryItems(activeItemEl, optionName) {
        let itemEls = [];
        if (optionName === "Carousel") {
            const carouselEl = activeItemEl.closest(".carousel");
            itemEls = [...carouselEl.querySelectorAll(".carousel-item")];
        }
        return itemEls;
    }

    /**
     * Updates the DOM with the reordered carousel items.
     *
     * @param {HTMLElement} activeItemEl the active item
     * @param {Array<HTMLElement>} itemEls the reordered items
     * @param {String} optionName
     */
    reorderCarouselItems(activeItemEl, itemEls, optionName) {
        if (optionName === "Carousel") {
            const carouselEl = activeItemEl.closest(".carousel");

            // Replace the content with the new slides.
            const carouselInnerEl = carouselEl.querySelector(".carousel-inner");
            const newCarouselInnerEl = document.createElement("div");
            newCarouselInnerEl.classList.add("carousel-inner");
            newCarouselInnerEl.append(...itemEls);
            carouselInnerEl.replaceWith(newCarouselInnerEl);

            // Update the indicators.
            const newPosition = itemEls.indexOf(activeItemEl);
            updateCarouselIndicators(carouselEl, newPosition);

            // Activate the active slide.
            this.dependencies["builderOptions"].setNextTarget(activeItemEl);
        }
    }
}

/**
 * Updates the carousel indicators to make the one at the given index be the
 * active one.
 *
 * @param {HTMLElement} carouselEl the carousel element
 * @param {Number} newPosition the index
 */
export function updateCarouselIndicators(carouselEl, newPosition) {
    const indicatorEls = carouselEl.querySelectorAll(".carousel-indicators > *");
    indicatorEls.forEach((indicatorEl, i) => {
        indicatorEl.classList.toggle("active", i === newPosition);
        indicatorEl.removeAttribute("aria-current");
        if (i === newPosition) {
            indicatorEl.setAttribute("aria-current", "true");
        }
    });
}
export class AddSlideAction extends BuilderAction {
    static id = "addSlide";
    static dependencies = ["carouselOption"];
    setup() {
        this.preview = false;
    }
    async apply({ editingElement }) {
        return this.dependencies.carouselOption.addSlide(editingElement);
    }
}
export class SlideCarouselAction extends BuilderAction {
    static id = "slideCarousel";
    static dependencies = ["carouselOption"];
    setup() {
        this.preview = false;
        this.withLoadingEffect = false;
    }
    async apply({ editingElement, params: { direction } }) {
        await this.dependencies.carouselOption.slideCarousel(editingElement, direction);
    }
}

export class ToggleControllersAction extends BuilderAction {
    static id = "toggleControllers";
    apply({ editingElement }) {
        const carouselEl = editingElement.closest(".carousel");
        const indicatorsEl = carouselEl.querySelector(".carousel-indicators");
        const areControllersHidden =
            carouselEl.classList.contains("s_carousel_arrows_hidden") &&
            indicatorsEl.classList.contains("s_carousel_indicators_hidden");
        carouselEl.classList.toggle("s_carousel_controllers_hidden", areControllersHidden);
    }
}
export class ToggleCardImgAction extends BuilderAction {
    static id = "toggleCardImg";
    apply({ editingElement }) {
        const carouselEl = editingElement.closest(".carousel");
        const cardEls = carouselEl.querySelectorAll(".card");
        for (const cardEl of cardEls) {
            const imageWrapperEl = renderToElement("website.s_carousel_cards.imageWrapper");
            cardEl.insertAdjacentElement("afterbegin", imageWrapperEl);
        }
    }
    clean({ editingElement: el }) {
        const carouselEl = el.closest(".carousel");
        carouselEl.querySelectorAll("figure").forEach((el) => el.remove());
    }
    isApplied({ editingElement }) {
        const carouselEl = editingElement.closest(".carousel");
        const cardImgEl = carouselEl.querySelector(".o_card_img_wrapper");
        return !!cardImgEl;
    }
}

registry.category("website-plugins").add(CarouselOptionPlugin.id, CarouselOptionPlugin);
