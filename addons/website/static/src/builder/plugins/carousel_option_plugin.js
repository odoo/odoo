import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { CarouselItemHeaderMiddleButtons } from "./carousel_item_header_buttons";
import { renderToElement } from "@web/core/utils/render";
import { BuilderAction } from "@html_builder/core/builder_action";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { StyleAction } from "@html_builder/core/core_builder_action_plugin";

/**
 * @typedef { Object } CarouselOptionShared
 * @property { CarouselOptionPlugin['addSlide'] } addSlide
 * @property { CarouselOptionPlugin['removeSlide'] } removeSlide
 * @property { CarouselOptionPlugin['slideCarousel'] } slideCarousel
 */

const carouselWrapperSelector =
    ".s_carousel_wrapper, .s_carousel_intro_wrapper, .s_carousel_cards_wrapper, .s_quotes_carousel_wrapper, .s_carousel_multiple_wrapper";
const carouselControlsSelector =
    ".carousel-control-prev, .carousel-control-next, .carousel-indicators";

const carouselClassicItemOptionSelector =
    ".s_carousel .carousel-item, .s_quotes_carousel .carousel-item, .s_carousel_intro .carousel-item, .s_carousel_cards .carousel-item";
const carouselMultipleItemOptionSelector = ".s_carousel_multiple .carousel-item";
const carouselItemOptionSelector =
    carouselClassicItemOptionSelector + ", " + carouselMultipleItemOptionSelector;

export class CarouselOptionPlugin extends Plugin {
    static id = "carouselOption";
    static dependencies = [
        "clone",
        "builderOptions",
        "builderActions",
        "builderOverlay",
        "history",
    ];
    static shared = ["addSlide", "removeSlide", "slideCarousel"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_header_middle_buttons: [
            {
                Component: CarouselItemHeaderMiddleButtons,
                selector: carouselItemOptionSelector,
                props: {
                    addSlide: this.addSlide.bind(this),
                    removeSlide: async (editingElement) => {
                        // Check if the slide is still in the DOM
                        // TODO: find a more general way to handle target element already removed by an option
                        if (editingElement.parentElement) {
                            const elementToRemove = editingElement.matches(
                                carouselMultipleItemOptionSelector
                            )
                                ? editingElement
                                : editingElement.closest(".carousel");
                            await this.removeSlide(elementToRemove);
                        }
                    },
                    applyAction: this.dependencies.builderActions.applyAction,
                },
            },
        ],
        container_title: {
            selector: carouselItemOptionSelector,
            getTitleExtraInfo: (editingElement) => this.getTitleExtraInfo(editingElement),
        },
        builder_actions: {
            AddSlideAction,
            SetAutoplayAction,
            SlideCarouselAction,
            ToggleControllersAction,
            ToggleCardImgAction,
            SetCarouselTypeAction,
            SetCarouselTimespanAction,
            SetCarouselDurationAction,
            ChangeSlidesToDisplayAction,
            SetSpacingStyleAction,
        },
        on_cloned_handlers: this.onCloned.bind(this),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
        gallery_items_providers: this.getGalleryItems.bind(this),
        reorder_items_processors: this.reorderCarouselItems.bind(this),
        on_will_save_handlers: this.restoreCarousels.bind(this),
        is_unremovable_selectors: carouselItemOptionSelector,
        // the carousel itself should be not contenteditable,
        // while its card items should
        content_not_editable_selectors: [".s_carousel_multiple"],
        content_editable_selectors: [".s_carousel_multiple .carousel-item"],
    };

    /**
     * Restores all the carousels so their first slide is the active one.
     */
    restoreCarousels(rootEl = this.editable) {
        // Set the first slide as the active one.
        for (const carouselEl of selectElements(rootEl, ".carousel")) {
            carouselEl.querySelectorAll(".carousel-item").forEach((itemEl, i) => {
                itemEl.classList.remove("next", "prev", "left", "right");
                itemEl.classList.toggle("active", i === 0);
            });
            carouselEl.querySelectorAll(".carousel-indicators > *").forEach((indicatorEl, i) => {
                indicatorEl.classList.toggle("active", i === 0);
                indicatorEl.setAttribute("aria-selected", "false");
                if (i === 0) {
                    indicatorEl.setAttribute("aria-selected", "true");
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
     * @param {HTMLElement} editingElement the current carousel-item element.
     */
    async addSlide(editingElement) {
        const carouselEl = editingElement.closest(".carousel");
        const isMultipleCarousel = carouselEl.classList.contains("s_carousel_multiple");
        const itemEls = [...carouselEl.querySelectorAll(".carousel-item")];
        const editingEl = isMultipleCarousel ? editingElement : editingElement.closest(".carousel");
        const newLength = itemEls.length + 1;
        const displayedSlides = Number(
            getComputedStyle(carouselEl).getPropertyValue("--o-carousel-multiple-items")
        );
        const minimumSlideToDisplay = isMultipleCarousel ? displayedSlides : 1;

        // Clone the active or current item and remove the "active" class.
        const activeItemEl = isMultipleCarousel
            ? editingElement
            : editingEl.querySelector(".carousel-item.active");
        const newItemEl = await this.dependencies.clone.cloneElement(activeItemEl, {
            activateClone: false,
        });
        newItemEl.classList.remove("active");
        newItemEl.id = `${editingElement.id}_${Date.now().toString(36)}`;

        if (newLength > minimumSlideToDisplay) {
            // Show the controllers (now that there are enough slides).
            const controlEls = carouselEl.querySelectorAll(carouselControlsSelector);
            controlEls.forEach((controlEl) => {
                controlEl.classList.remove("d-none");
            });
        }

        // Add the new indicator.
        const activeIndicatorEl = editingElement.querySelector(
            ".carousel-indicators button.active"
        );
        const newIndicatorEl = activeIndicatorEl.cloneNode(true);
        newIndicatorEl.setAttribute("aria-controls", newItemEl.id);
        newIndicatorEl.setAttribute("aria-selected", "false");
        activeIndicatorEl.after(newIndicatorEl);
        this.updateIndicatorsLabels(editingElement);

        // Slide to the next item.
        if (isMultipleCarousel) {
            await this.slide(carouselEl, "next", newItemEl);
        } else {
            await this.slide(carouselEl, "next");
        }
    }

    /**
     * Removes the current slide.
     *
     * @param {HTMLElement} editingElement the current carousel-item element.
     */
    async removeSlide(editingElement) {
        const carouselEl = editingElement.closest(".carousel");
        const isMultipleCarousel = carouselEl.classList.contains("s_carousel_multiple");
        const itemEls = [...carouselEl.querySelectorAll(".carousel-item")];
        const editingEl = isMultipleCarousel ? editingElement : editingElement.closest(".carousel");
        const newLength = itemEls.length - 1;
        const displayedSlides = getComputedStyle(carouselEl).getPropertyValue(
            "--o-carousel-multiple-items"
        );
        const minimumSlideToDisplay = isMultipleCarousel ? displayedSlides : 1;

        if (newLength > 0) {
            const activeItemEl = isMultipleCarousel
                ? editingEl
                : editingEl.querySelector(".carousel-item.active");

            if (isMultipleCarousel) {
                const newSelectedItemEl =
                    activeItemEl.previousElementSibling || activeItemEl.nextElementSibling;
                const hasActiveClassItemIndex = itemEls.findIndex((item) =>
                    item.classList.contains("active")
                );
                const countAfter = itemEls.length - hasActiveClassItemIndex - 1;
                if (activeItemEl.classList.contains("active")) {
                    newSelectedItemEl.classList.add("active");
                }
                if (countAfter < displayedSlides && newLength >= displayedSlides) {
                    await this.slide(carouselEl, "prev", newSelectedItemEl);
                } else {
                    await this.dependencies["builderOptions"].setNextTarget(newSelectedItemEl);
                }
            } else {
                // Slide to the previous item.
                await this.slide(carouselEl, "prev");
            }

            // Remove the carousel item and the last not active indicator.
            activeItemEl.remove();
            const indicatorEls = carouselEl.querySelectorAll(".carousel-indicators :not(.active)");
            Array.from(indicatorEls).at(-1)?.remove();

            // Hide the controllers if there is only one slide left.
            const controlEls = carouselEl.querySelectorAll(carouselControlsSelector);
            controlEls.forEach((controlEl) =>
                controlEl.classList.toggle("d-none", newLength <= minimumSlideToDisplay)
            );
        }
        this.updateIndicatorsLabels(editingElement);
    }

    /**
     * Slides the carousel.
     *
     * @param {HTMLElement} editingElement the carousel element.
     * @param {String} direction "prev" or "next".
     * @param {Element} nextTargetElement the next targeted carousel element (optional).
     */
    async slideCarousel(editingElement, direction, nextTargetElement) {
        await this.slide(editingElement, direction, nextTargetElement);
    }

    /**
     * Slides the carousel in the given direction.
     *
     * @param {String|Number} direction the direction in which to slide:
     *     - "prev": the previous slide;
     *     - "next": the next slide;
     *     - number: a slide number.
     * @param {Element} editingElement the carousel element.
     * @param {Element} nextTargetElement the next targeted carousel element (optional).
     * @returns {Promise}
     */
    slide(editingElement, direction, nextTargetElement) {
        const isMultipleCarousel = editingElement.classList.contains("s_carousel_multiple");
        editingElement.addEventListener(
            "slide.bs.carousel",
            () => {
                if (isMultipleCarousel) {
                    this.dependencies.builderOverlay.toggleOverlaysVisibility(false);
                }
                this.slideTimestamp = window.performance.now();
            },
            { once: true }
        );

        return new Promise((resolve) => {
            const itemsEls = editingElement.querySelectorAll(".carousel-item");
            const activeItemEl = editingElement.querySelector(".carousel-item.active");
            const displayedSlides = Number(
                getComputedStyle(editingElement).getPropertyValue("--o-carousel-multiple-items")
            );
            const currentIndex = activeItemEl ? Array.from(itemsEls).indexOf(activeItemEl) : -1;
            let newIndex;

            const setNextTarget = () => {
                const activeItemEl = editingElement.querySelector(".carousel-item.active");
                const targetElement = nextTargetElement || activeItemEl;
                if (this.dependencies.history.getIsCurrentStepModified()) {
                    this.dependencies["builderOptions"].setNextTarget(targetElement);
                } else {
                    // if we don't have any modifications at the current step, we need to
                    // force the update of the containers
                    this.dependencies["builderOptions"].updateContainers(targetElement, {
                        forceUpdate: true,
                    });
                }
            };

            editingElement.addEventListener(
                "slid.bs.carousel",
                () => {
                    // slid.bs.carousel is most of the time fired too soon by
                    // bootstrap since it emulates the transitionEnd with a
                    // setTimeout. We wait here an extra 20% of the time before
                    // retargeting edition, which should be enough...
                    const slideDuration = window.performance.now() - this.slideTimestamp;
                    setTimeout(() => {
                        // Setting the active indicator manually, as Bootstrap
                        // could not do it because the `data-bs-slide-to`
                        // attribute is not here in edit mode anymore.
                        const itemEls = editingElement.querySelectorAll(".carousel-item");
                        const activeItemEl = editingElement.querySelector(".carousel-item.active");
                        const activeIndex = [...itemEls].indexOf(activeItemEl);
                        const indicatorEls = editingElement.querySelectorAll(
                            ".carousel-indicators > *"
                        );
                        const activeIndicatorEl = [...indicatorEls][activeIndex];
                        activeIndicatorEl.classList.add("active");
                        activeIndicatorEl.setAttribute("aria-selected", "true");

                        // Activate the active item.
                        this.dependencies["builderOptions"].setNextTarget(activeItemEl);

                        resolve();
                    }, 0.2 * slideDuration);
                },
                { once: true }
            );

            // For multiple carousel, wait for the carousel-inner transition to complete
            // before refreshing overlays to avoid misalignment during the slide animation
            if (isMultipleCarousel) {
                const carouselInner = editingElement.querySelector(".carousel-inner");
                carouselInner.addEventListener("transitionend", setNextTarget, { once: true });
            }

            const carouselInstance = window.Carousel.getOrCreateInstance(editingElement, {
                ride: false,
                pause: true,
                keyboard: false,
            });
            if (typeof direction === "number") {
                if (direction !== currentIndex) {
                    carouselInstance.to(direction);
                } else {
                    // No slide needed, directly activate the next target
                    setNextTarget();
                    resolve();
                }
            } else {
                if (isMultipleCarousel) {
                    if (displayedSlides >= itemsEls.length) {
                        setNextTarget();
                        resolve();
                        return;
                    }
                    if (direction === "prev") {
                        if (currentIndex <= 0) {
                            newIndex = itemsEls.length - displayedSlides;
                        } else {
                            newIndex = currentIndex - 1;
                        }
                    } else if (direction === "next") {
                        if (currentIndex >= itemsEls.length - displayedSlides) {
                            newIndex = 0;
                        } else {
                            newIndex = currentIndex + 1;
                        }
                    }
                    carouselInstance.to(newIndex);
                } else {
                    carouselInstance[direction]();
                }
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
            const isMultipleCarousel = carouselEl.classList.contains("s_carousel_multiple");

            // Replace the content with the new slides.
            const carouselInnerEl = carouselEl.querySelector(".carousel-inner");
            const newCarouselInnerEl = document.createElement("div");
            if (isMultipleCarousel) {
                // We need to keep the current ".carousel-inner" element to avoid glitch with
                // the translateX transform.
                carouselInnerEl.querySelectorAll(".carousel-item").forEach((item) => item.remove());
                carouselInnerEl.append(...itemEls);
            } else {
                carouselInnerEl.replaceWith(newCarouselInnerEl);
                newCarouselInnerEl.append(...itemEls);
                newCarouselInnerEl.classList.add("carousel-inner");

                // Update the indicators.
                const newPosition = itemEls.indexOf(activeItemEl);
                updateCarouselIndicators(carouselEl, newPosition);
            }

            // Activate the active slide.
            this.dependencies.builderOptions.setNextTarget(activeItemEl);
        }
    }
    /**
     * @param {HTMLElement} editingElement the carousel element
     */
    updateIndicatorsLabels(editingElement) {
        const indicatorEls = editingElement.querySelectorAll(".carousel-indicators > *");
        for (const indicatorEl of indicatorEls) {
            updateIndicatorLabel(indicatorEl, indicatorEls);
        }
    }
}

/**
 * @param {HTMLElement} indicatorEl one indicator
 * @param {HTMLCollection|NodeList|HTMLElement[]} siblingEls all indicators
 */
export function updateIndicatorLabel(indicatorEl, siblingEls) {
    indicatorEl.setAttribute(
        "aria-label",
        _t("Slide %(itemIndex)s of %(total)s", {
            itemIndex: [...siblingEls].indexOf(indicatorEl) + 1,
            total: siblingEls.length,
        })
    );
}

/**
 * Updates the carousel indicators to make the one at the given index be the
 * active one, as well as update the aria-labels.
 *
 * @param {HTMLElement} carouselEl the carousel element
 * @param {Number} newPosition the index
 */
export function updateCarouselIndicators(carouselEl, newPosition) {
    const indicatorEls = carouselEl.querySelectorAll(".carousel-indicators > *");
    indicatorEls.forEach((indicatorEl, i) => {
        updateIndicatorLabel(indicatorEl, indicatorEls);
        indicatorEl.classList.toggle("active", i === newPosition);
        indicatorEl.setAttribute("aria-selected", "false");
        if (i === newPosition) {
            indicatorEl.setAttribute("aria-selected", "true");
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

export class SetAutoplayAction extends BuilderAction {
    static id = "setAutoplay";
    isApplied({ editingElement, params: { bsRide } }) {
        return editingElement.dataset.bsRide === bsRide;
    }
    apply({ editingElement, params: { bsRide, ariaLive } }) {
        editingElement.dataset.bsRide = bsRide;
        editingElement.querySelector(".carousel-inner")?.setAttribute("aria-live", ariaLive);
    }
}

export class SlideCarouselAction extends BuilderAction {
    static id = "slideCarousel";
    static dependencies = ["carouselOption"];
    setup() {
        this.preview = false;
        this.withLoadingEffect = false;
    }
    async apply({ editingElement, params: { direction, nextTargetElement } }) {
        await this.dependencies.carouselOption.slideCarousel(
            editingElement,
            direction,
            nextTargetElement
        );
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

function getTransitionDuration(el) {
    if (el.matches(".carousel-instant")) {
        return 0;
    }

    const customDuration = parseInt(el.style.getPropertyValue("--transition-duration"));
    if (customDuration) {
        return customDuration;
    }

    const carouselItemEl = el.querySelector(".carousel-item");
    if (carouselItemEl) {
        return parseFloat(getComputedStyle(carouselItemEl).transitionDuration) * 1000;
    }

    // Default Bootstrap carousel transition duration
    return 600;
}

function updateCarouselType(el, typeClass) {
    el.classList.add("slide");
    el.classList.remove("carousel-fade", "carousel-instant");
    if (typeClass) {
        el.classList.add(typeClass);
    }
}

export class SetCarouselTypeAction extends BuilderAction {
    static id = "setCarouselType";
    isApplied({ editingElement, params: { mainParam: carouselTypeClass } }) {
        if (carouselTypeClass) {
            return editingElement.classList.contains(carouselTypeClass);
        }
        return !(
            editingElement.classList.contains("carousel-fade") ||
            editingElement.classList.contains("carousel-instant")
        );
    }
    apply({ editingElement, params: { mainParam: carouselTypeClass } }) {
        const wasCarouselInstant = editingElement.classList.contains("carousel-instant");
        const isCarouselInstant = carouselTypeClass === "carousel-instant";

        if (wasCarouselInstant !== isCarouselInstant) {
            if (wasCarouselInstant) {
                // Remove the class "carousel-instant" before to compute the
                // duration (otherwise transition-duration equals 0s)
                updateCarouselType(editingElement, carouselTypeClass);
            }

            const duration = getTransitionDuration(editingElement);
            const timespan = parseInt(editingElement.dataset.bsInterval, 10) || 1000;
            editingElement.dataset.bsInterval =
                timespan + (isCarouselInstant ? -duration : duration);

            if (!wasCarouselInstant) {
                // Add the class "carousel-instant" after to compute the
                // duration (otherwise transition-duration equals 0s)
                updateCarouselType(editingElement, carouselTypeClass);
            }
        } else {
            updateCarouselType(editingElement, carouselTypeClass);
        }
    }
}

export class SetCarouselTimespanAction extends BuilderAction {
    static id = "setCarouselTimespan";
    setup() {
        this.preview = false;
    }
    apply({ editingElement, value }) {
        const duration = getTransitionDuration(editingElement);
        const timespan = parseInt(value, 10);
        editingElement.dataset.bsInterval = timespan + duration;
    }
    getValue({ editingElement }) {
        const duration = getTransitionDuration(editingElement);
        const timespan = parseInt(editingElement.dataset.bsInterval, 10) || 1000;
        return timespan - duration;
    }
}

export class SetCarouselDurationAction extends BuilderAction {
    static id = "setCarouselDuration";
    setup() {
        this.preview = false;
    }
    apply({ editingElement, value }) {
        if (!value) {
            return;
        }
        const duration = getTransitionDuration(editingElement);
        const timespan = parseInt(editingElement.dataset.bsInterval, 10) || 1000;
        const newDuration = parseInt(value, 10);
        editingElement.dataset.bsInterval = timespan + (newDuration - duration);
        editingElement.style.setProperty("--transition-duration", value);
    }
    getValue({ editingElement }) {
        const duration = getTransitionDuration(editingElement);
        return duration;
    }
}

export class ChangeSlidesToDisplayAction extends BuilderAction {
    static id = "changeSlidesToDisplay";
    static dependencies = ["carouselOption"];

    load({ editingElement: el }) {
        const displayedNumberClass = [...el.classList].find((className) =>
            className.startsWith("o_displayed_items_")
        );
        return (displayedNumberClass && parseInt(displayedNumberClass?.split("_").at(-1))) || 1;
    }

    async apply({ editingElement: el, value, loadResult: displayedItemsNumber }) {
        if (displayedItemsNumber === parseInt(value)) {
            return;
        }

        // Restart the slider when we change the number of displayed slides.
        const itemsEls = el.querySelectorAll(".carousel-item");
        const activeItemEl = el.querySelector(".carousel-item.active");
        const activeItemIndex = Array.from(itemsEls).indexOf(activeItemEl);
        if (activeItemIndex != 0) {
            await this.dependencies.carouselOption.slideCarousel(el, 0, itemsEls[0]);
        }
    }
}

export class SetSpacingStyleAction extends StyleAction {
    static id = "setSpacingStyle";

    applyCssStyle({ editingElement, params = {}, value }) {
        const carouselInner = editingElement.querySelector(".carousel-inner");
        const computedStyle = getComputedStyle(carouselInner);
        const transition = computedStyle.transition;
        const transform = computedStyle.transform;
        carouselInner.style.transition = "none";
        super.applyCssStyle({ editingElement, params, value });
        carouselInner.style.transform = transform;
        void carouselInner.offsetWidth;
        carouselInner.style.transition = transition;
    }
}

registry.category("website-plugins").add(CarouselOptionPlugin.id, CarouselOptionPlugin);
