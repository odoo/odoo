import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";
import { getCarouselCenteringIndex } from "@website/utils/misc";
import { carouselControlsSelector } from "./carousel_option_plugin";
import { CarouselMultipleItemHeaderMiddleButtons } from "./carousel_multiple_item_header_buttons";

/**
 * @typedef { Object } CarouselMultipleOptionShared
 * @property { CarouselMultipleOptionPlugin['addSlide'] } addSlide
 * @property { CarouselMultipleOptionPlugin['removeSlide'] } removeSlide
 * @property { CarouselOptionPlugin['slideCarousel'] } slideCarousel
 * @property { CarouselOptionPlugin['updateControllers'] } updateControllers
 */

export class CarouselMultipleOptionPlugin extends Plugin {
    static id = "carouselMultipleOption";
    static dependencies = [
        "builderOptions",
        "builderActions",
        "builderOverlay",
        "carouselOption",
        "clone",
        "domObserver",
    ];
    static shared = ["addSlide", "removeSlide", "slideCarousel", "updateControllers"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_header_middle_buttons: {
            Component: CarouselMultipleItemHeaderMiddleButtons,
            selector: ".s_carousel_multiple_item",
            props: {
                addSlide: this.addSlide.bind(this),
                removeSlide: async (editingElement) => {
                    // Check if the slide is still in the DOM
                    // TODO: find a more general way to handle target element already removed by an option
                    if (editingElement.parentElement) {
                        await this.removeSlide(editingElement);
                    }
                },
                applyAction: this.dependencies.builderActions.applyAction,
            },
        },
        container_title: {
            selector: ".s_carousel_multiple_item",
            getTitleExtraInfo: this.dependencies.carouselOption.getTitleExtraInfo,
        },
        builder_actions: {
            AddCarouselMultipleSlideAction,
            SlideCarouselMultipleAction,
            ChangeSlidesToDisplayAction,
        },
        on_cloned_handlers: this.onCloned.bind(this),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
        on_will_save_handlers: this.restoreCarousels.bind(this),
        on_mobile_view_switched_handlers: this.onMobileViewSwitched.bind(this),
        reorder_items_processors: this.reorderCarouselItems.bind(this),
        is_unremovable_selectors: ".s_carousel_multiple_item",
    };

    restoreCarousels(rootEl = this.editable) {
        const proms = [];
        // Restore all the carousels so their first slide is the active one.
        for (const carouselEl of rootEl.querySelectorAll(".s_carousel_multiple")) {
            proms.push(this.slideCarousel(carouselEl, 0));
        }
        return Promise.all(proms);
    }

    onMobileViewSwitched() {
        // Reset the carousel when toggling the mobile view.
        for (const carouselEl of this.editable.querySelectorAll(".s_carousel_multiple")) {
            this.dependencies.domObserver.ignore(() => this.slideCarousel(carouselEl, 0));
        }
    }

    /**
     * Adds a slide.
     *
     * @param {HTMLElement} editingElement current carousel-item element or
     * carousel element.
     */
    async addSlide(editingElement) {
        const carouselEl = editingElement.closest(".carousel");
        const itemEls = [...carouselEl.querySelectorAll(".carousel-item")];
        const newLength = itemEls.length + 1;
        const nbDisplayedSlides = Number(
            getComputedStyle(carouselEl).getPropertyValue("--carousel-multiple-items-per-slide")
        );

        // Clone the editing element, if it's the card item, or the first item
        // of the carousel, otherwise.
        const itemEl = editingElement.matches(".carousel-item") ? editingElement : itemEls[0];
        const newItemEl = await this.dependencies.clone.cloneElement(itemEl, {
            activateClone: false,
        });
        newItemEl.classList.remove("active");
        newItemEl.id = `${carouselEl.id}_${Date.now().toString(36)}`;

        this.updateControllers(carouselEl);
        // Slide to the next item.
        const direction = getCarouselCenteringIndex(newItemEl) ?? 0;
        if (newLength > nbDisplayedSlides) {
            await this.slideCarousel(carouselEl, direction, newItemEl);
        } else {
            this.dependencies.builderOptions.setNextTarget(newItemEl);
        }
    }

    /**
     * Removes the current slide.
     *
     * @param {HTMLElement} editingElement the current carousel-item element.
     */
    async removeSlide(editingElement) {
        const carouselEl = editingElement.closest(".carousel");
        const itemEls = [...carouselEl.querySelectorAll(".carousel-item")];
        const newLength = itemEls.length - 1;
        const nbDisplayedSlides = Number(
            getComputedStyle(carouselEl).getPropertyValue("--carousel-multiple-items-per-slide")
        );

        const newSelectedItemEl =
            editingElement.previousElementSibling || editingElement.nextElementSibling;
        const activeItemEl = carouselEl.querySelector(".carousel-item.active");
        const currentIndex = itemEls.indexOf(activeItemEl);
        if (currentIndex === itemEls.length - nbDisplayedSlides && newLength >= nbDisplayedSlides) {
            await this.slideCarousel(carouselEl, currentIndex - 1, newSelectedItemEl);
        } else {
            this.dependencies.builderOptions.setNextTarget(newSelectedItemEl);
        }
        // Remove the carousel item.
        editingElement.remove();
        this.updateControllers(carouselEl);
    }

    /**
     * Shows or hides the controllers and updates the number of indicators.
     *
     * @param {HTMLElement} carouselEl the carousel element.
     */
    updateControllers(carouselEl) {
        const itemEls = [...carouselEl.querySelectorAll(".carousel-item")];
        const length = itemEls.length;
        const nbDisplayedSlides = Number(
            getComputedStyle(carouselEl).getPropertyValue("--carousel-multiple-items-per-slide")
        );
        const controlEls = carouselEl.querySelectorAll(carouselControlsSelector);
        // Show or hide the controllers.
        controlEls.forEach((controlEl) => {
            controlEl.classList.toggle("d-none", length <= nbDisplayedSlides);
        });

        let indicatorEls = [...carouselEl.querySelectorAll(".carousel-indicators > button")];
        indicatorEls = indicatorEls.filter(
            (indicatorEl) => getComputedStyle(indicatorEl).display !== "none"
        );
        // Add new indicators if there aren't enough.
        while (indicatorEls.length < length - nbDisplayedSlides + 1) {
            const activeIndicatorEl = carouselEl.querySelector(
                ".carousel-indicators button.active"
            );
            const newIndicatorEl = activeIndicatorEl.cloneNode(true);
            newIndicatorEl.classList.remove("active");
            const itemEl = itemEls[indicatorEls.length];
            newIndicatorEl.setAttribute("aria-controls", itemEl.id);
            newIndicatorEl.setAttribute("aria-selected", "false");
            indicatorEls.at(-1).insertAdjacentElement("afterend", newIndicatorEl);
            indicatorEls.push(newIndicatorEl);
        }
        // Remove indicators if there are too many.
        while (indicatorEls.length > length - nbDisplayedSlides + 1) {
            // Remove last not active indicator.
            const lastNotActiveIndex = indicatorEls.findLastIndex(
                (indicatorEl) => !indicatorEl.classList.contains("active")
            );
            if (lastNotActiveIndex === -1) {
                break;
            }
            indicatorEls[lastNotActiveIndex].remove();
            indicatorEls.splice(lastNotActiveIndex, 1);
        }
    }

    /**
     * Slides the carousel.
     *
     * @param {HTMLElement} carouselEl the carousel element.
     * @param {Number} direction the slide number to slide to.
     * @param {HTMLElement} [nextTargetElement] element to activate.
     */
    async slideCarousel(carouselEl, direction, nextTargetElement = carouselEl) {
        const itemEls = [...carouselEl.querySelectorAll(".carousel-item")];
        const activeItemEl = carouselEl.querySelector(".carousel-item.active");
        const displayedSlides = Number(
            getComputedStyle(carouselEl).getPropertyValue("--carousel-multiple-items-per-slide")
        );
        const currentIndex = itemEls.indexOf(activeItemEl);
        if (direction !== currentIndex && (displayedSlides < itemEls.length || direction === 0)) {
            await this.slide(carouselEl, direction);
            this.dependencies.builderOptions.setNextTarget(nextTargetElement);
            return;
        }
        // No slide happens, but we need to update containers
        this.dependencies.builderOptions.updateContainers(nextTargetElement);
    }

    /**
     * Slides the carousel in the given direction.
     *
     * @param {HTMLElement} carouselEl the carousel element.
     * @param {Number} direction the slide number to slide to.
     * @returns {Promise}
     */
    slide(carouselEl, direction) {
        carouselEl.style.setProperty("--carousel-multiple-current-index", direction);
        const transitionPromise = new Promise((resolve) => {
            const carouselInnerEl = carouselEl.querySelector(".carousel-inner");
            carouselInnerEl.addEventListener("transitionend", resolve, { once: true });
        });
        const slidPromise = this.dependencies.carouselOption.slideCarousel(...arguments);

        return Promise.all([slidPromise, transitionPromise]);
    }

    onCloned({ cloneEl }) {
        if (cloneEl.matches(".s_carousel_multiple_wrapper")) {
            this.dependencies.carouselOption.assignUniqueID(cloneEl);
        }
    }

    onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(".s_carousel_multiple_wrapper")) {
            this.dependencies.carouselOption.assignUniqueID(snippetEl);
        }
    }

    /**
     * Updates the DOM with the reordered carousel items.
     *
     * @param {HTMLElement} activeItemEl the active item
     * @param {Array<HTMLElement>} itemEls the reordered items
     * @param {String} optionName
     */
    reorderCarouselItems(activeItemEl, itemEls, optionName) {
        if (optionName === "Carousel" && activeItemEl.matches(".s_carousel_multiple_item")) {
            const carouselEl = activeItemEl.closest(".carousel");
            // Replace the content with the new slides.
            const carouselInnerEl = carouselEl.querySelector(".carousel-inner");
            // We need to keep the current ".carousel-inner" element to avoid glitch with
            // the translateX transform.
            carouselInnerEl.querySelectorAll(".carousel-item").forEach((item) => item.remove());
            carouselInnerEl.append(...itemEls);
            const newPosition = getCarouselCenteringIndex(activeItemEl);
            if (newPosition >= 0) {
                this.slideCarousel(carouselEl, newPosition, activeItemEl);
                return;
            }
            // Activate the active slide.
            this.dependencies.builderOptions.setNextTarget(activeItemEl);
        }
    }
}

export class AddCarouselMultipleSlideAction extends BuilderAction {
    static id = "addCarouselMultipleSlide";
    static dependencies = ["carouselMultipleOption"];
    setup() {
        this.preview = false;
    }
    async apply({ editingElement }) {
        return this.dependencies.carouselMultipleOption.addSlide(editingElement);
    }
}

export class SlideCarouselMultipleAction extends BuilderAction {
    static id = "slideCarouselMultiple";
    static dependencies = ["carouselMultipleOption"];
    setup() {
        this.preview = false;
        this.withLoadingEffect = false;
    }
    async apply({ editingElement, params: { direction, nextTargetElement } }) {
        await this.dependencies.carouselMultipleOption.slideCarousel(
            editingElement,
            direction,
            nextTargetElement
        );
    }
}

export class ChangeSlidesToDisplayAction extends BuilderAction {
    static id = "changeSlidesToDisplay";
    static dependencies = ["carouselMultipleOption"];

    async apply({ editingElement: el }) {
        // When changing the number of slides to display, we also need to
        // update carousel controllers, because they may have been shown/hidden
        // when we added/removed cards.
        this.dependencies.carouselMultipleOption.updateControllers(el);
    }
}

registry
    .category("website-plugins")
    .add(CarouselMultipleOptionPlugin.id, CarouselMultipleOptionPlugin);
