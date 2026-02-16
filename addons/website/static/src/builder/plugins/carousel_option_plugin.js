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
import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { patch } from "@web/core/utils/patch";
import { MovePlugin } from "@html_builder/core/move_plugin";
import { RemovePlugin } from "@html_builder/core/remove_plugin";
import { ClonePlugin } from "@html_builder/core/clone_plugin";
import { quoteCarouselSelector } from "@html_builder/plugins/utils";

/**
 * @typedef { Object } CarouselOptionShared
 * @property { CarouselOptionPlugin['addSlide'] } addSlide
 * @property { CarouselOptionPlugin['removeSlide'] } removeSlide
 * @property { CarouselOptionPlugin['slideCarousel'] } slideCarousel
 */

export const CAROUSEL_CARDS_SEQUENCE = between(WEBSITE_BACKGROUND_OPTIONS, BOX_BORDER_SHADOW);

const carouselWrapperSelector =
    ".s_carousel_wrapper, .s_carousel_intro_wrapper, .s_carousel_cards_wrapper, .s_quotes_carousel_wrapper";
const carouselControlsSelector =
    ".carousel-control-prev, .carousel-control-next, .carousel-indicators";

const carouselItemOptionSelector =
    ".s_carousel .carousel-item, .s_quotes_carousel .carousel-item, .s_carousel_intro .carousel-item, .s_carousel_cards .carousel-item";

export class CarouselOption extends BaseOptionComponent {
    static template = "website.CarouselOption";
    static selector = "section";
    static exclude =
        ".s_carousel_intro_wrapper, .s_carousel_cards_wrapper, .s_quotes_carousel_wrapper:has(>.s_quotes_carousel_compact)";
    static applyTo = ":scope > .carousel";
    setup() {
        super.setup();
        this.state = useDomState((editingElement) => {
            const isQuoteCarousel = editingElement.closest(quoteCarouselSelector);
            if (!isQuoteCarousel) {
                return { shouldHide: false };
            }
            return {
                shouldHide:
                    editingElement.dataset.scrollMode === "single" &&
                    editingElement.dataset.numberOfElements !== "1",
            };
        });
    }
}

export class CarouselBottomControllersOption extends BaseOptionComponent {
    static template = "website.CarouselBottomControllersOption";
    static selector = "section";
    static applyTo = ".s_carousel_intro, .s_quotes_carousel_compact";
}

export class CarouselCardsOption extends BaseOptionComponent {
    static template = "website.CarouselCardsOption";
    static selector = "section";
    static applyTo = ".s_carousel_cards";
}

export class CarouselQuotesLayoutOption extends BaseOptionComponent {
    static template = "website.CarouselQuotesLayoutOptions";
    static selector =
        "section[data-snippet='s_quotes_carousel'], section[data-snippet='s_quotes_carousel_minimal']";
    static applyTo = ".s_quotes_carousel";
}

export class CarouselOptionPlugin extends Plugin {
    static id = "carouselOption";
    static dependencies = ["clone", "builderOptions", "builderActions"];
    static shared = ["addSlide", "removeSlide", "slideCarousel"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [
            CarouselOption,
            CarouselBottomControllersOption,
            withSequence(CAROUSEL_CARDS_SEQUENCE, CarouselCardsOption),
            CarouselQuotesLayoutOption,
        ],
        builder_header_middle_buttons: {
            Component: CarouselItemHeaderMiddleButtons,
            selector: carouselItemOptionSelector,
            props: {
                addSlide: (editingElement) => this.addSlide(editingElement),
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
            UpdateCarouselLayoutAction,
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
        for (const carouselEl of selectElements(rootEl, ".carousel")) {
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
     * Return the active or focused slide element.
     *
     * @param {HTMLElement} editingElement the carousel element.
     */
    getActiveOrFocusedSlide(editingElement) {
        if (editingElement) {
            const className =
                editingElement?.dataset.scrollMode === "single" ? "o-focused-slide" : "active";
            return editingElement.querySelector(`.carousel-item.${className}`);
        }
    }

    /**
     * Adds a slide.
     *
     * @param {HTMLElement} editingElement the carousel element.
     */
    async addSlide(editingElement) {
        // Clone the active item and remove the "active" class.
        const activeItemEl = this.getActiveOrFocusedSlide(editingElement);
        const newItemEl = await this.dependencies.clone.cloneElement(activeItemEl, {
            activateClone: false,
        });
        // No additional handling is required for the Quotes carousel, except
        // for the compact variant, since the remaining cases are already
        // covered by the patched Clone plugin.
        if (
            editingElement.closest(quoteCarouselSelector) ||
            newItemEl.classList.contains("s_blockquote")
        ) {
            return;
        }
        newItemEl.classList.remove("active");

        // Show the controllers (now that there is always more than one item).
        const controlEls = editingElement.querySelectorAll(carouselControlsSelector);
        controlEls.forEach((controlEl) => {
            controlEl.classList.remove("d-none");
        });

        // Add the new indicator.
        const indicatorsEl = editingElement.querySelector(".carousel-indicators");
        addIndicatorButton("", editingElement.id, indicatorsEl);

        // Slide to the new item.
        await slide(
            editingElement,
            this.dependencies["builderOptions"],
            this.slideTimestamp,
            "next"
        );
    }

    /**
     * Removes the current slide.
     *
     * @param {HTMLElement} editingElement the carousel element.
     */
    async removeSlide(editingElement) {
        const itemEls = [...editingElement.querySelectorAll(".carousel-item")];
        const scrollMode = editingElement.dataset.scrollMode;
        const numberOfElements = parseInt(editingElement.dataset.numberOfElements);
        const shouldSlide = scrollMode === "all" || itemEls.length > numberOfElements;
        const isQuoteCarousel = editingElement.closest(quoteCarouselSelector);
        const newLength = itemEls.length - 1;
        if (newLength > 0) {
            const selectedItemEl = this.getActiveOrFocusedSlide(editingElement);
            const activeIndicatorEl = editingElement.querySelector(
                ".carousel-indicators > .active"
            );
            // Should not slide if carousel items count is less than or equal
            // to numberOfElements especially in single scroll mode.
            if (shouldSlide || !isQuoteCarousel) {
                // Slide to the previous item.
                await slide(
                    editingElement,
                    this.dependencies["builderOptions"],
                    this.slideTimestamp,
                    "prev"
                );
            }

            // Remove the carousel item and the indicator.
            selectedItemEl.remove();
            activeIndicatorEl?.remove();

            // If we didn't slide and the removed item was active, then we need
            // to manually activate the first slide for quote carousel.
            if (!shouldSlide && selectedItemEl.classList.contains("active") && isQuoteCarousel) {
                const firstSlideEl = editingElement.querySelector(".carousel-slide");
                firstSlideEl.classList.add("active");
            }

            // Hide the controllers if the slide count is one or less than
            // numberOfElements as per scrollMode.
            const controlEls = editingElement.querySelectorAll(carouselControlsSelector);
            const isSingleMode = editingElement.dataset.scrollMode === "single";
            const shouldHide = isSingleMode ? newLength <= numberOfElements : newLength <= 1;
            controlEls.forEach((controlEl) => controlEl.classList.toggle("d-none", shouldHide));
            updateSlideIndex(editingElement);
        }
    }

    /**
     * Slides the carousel.
     *
     * @param {HTMLElement} editingElement the carousel element.
     * @param {String} direction "prev" or "next".
     */
    async slideCarousel(editingElement, direction) {
        await slide(
            editingElement,
            this.dependencies["builderOptions"],
            this.slideTimestamp,
            direction
        );
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

            itemEls.forEach((itemEl, index) => {
                itemEl.dataset.index = index;
            });
            const scrollMode = carouselEl.dataset.scrollMode;
            const newPosition = itemEls.indexOf(activeItemEl);

            // Replace the content with the new slides.
            const carouselInnerEl = carouselEl.querySelector(".carousel-inner");
            carouselInnerEl.replaceChildren(...itemEls);

            // Update the index of each element.
            updateSlideIndex(carouselInnerEl);
            if (scrollMode === "single") {
                itemEls.forEach((itemEl) => {
                    itemEl.classList.remove("active", "o-focused-slide");
                });
                itemEls[0].classList.add("active", "o-focused-slide");
                this.dependencies.builderOptions.setNextTarget(itemEls[0]);
            } else {
                // Update the indicators.
                updateCarouselIndicators(carouselEl, newPosition);
                // Activate the active slide.
                this.dependencies.builderOptions.setNextTarget(activeItemEl);
            }
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

export class UpdateCarouselLayoutAction extends BuilderAction {
    static id = "updateQuotesCarouselLayout";
    static dependencies = ["builderOptions"];

    apply({ editingElement }) {
        const activeSlideEl = triggerQuotesCarouselRebuild(editingElement);
        this.dependencies.builderOptions.setNextTarget(activeSlideEl);
    }
}

/**
 * Update the index of each slide.
 *
 * @param {HTMLElement} editingElement the carousel element.
 */
function updateSlideIndex(editingElement) {
    const carouselSlideEls = editingElement.querySelectorAll(".carousel-slide");
    carouselSlideEls.forEach((carouselSlideEl, index) => {
        carouselSlideEl.dataset.index = index;
    });
}

/**
 * Adds an indicator button to the carousel’s indicator container.
 *
 * @param {number} index – The slide index that this indicator represents.
 * @param {string} editingElementId – The ID of the carousel root element.
 * @param {HTMLElement} indicatorEl – The indicator container to append button.
 */
function addIndicatorButton(index, editingElementId, indicatorEl) {
    const btnEl = document.createElement("button");
    btnEl.type = "button";
    btnEl.dataset.bsTarget = `#${editingElementId}`;
    btnEl.dataset.bsSlideTo = index.toString();
    btnEl.setAttribute("aria-label", _t("Carousel indicator"));
    btnEl.classList.add(...(index === 0 ? ["active"] : []));
    indicatorEl.appendChild(btnEl);
}

/**
 * Replaces all classes on the element that start with given prefix and adds
 * the provided class.
 *
 * @param {HTMLElement} el - The element whose classes will be updated.
 * @param {string} classToAdd - The class to add to the element.
 * @param {string} classPrefix - The prefix used to identify classes to remove.
 */
function modifyElementClass(el, classToAdd, classPrefix) {
    const classesToRemove = Array.from(el.classList).filter((cls) => cls.startsWith(classPrefix));
    el.classList.remove(...classesToRemove);
    el.classList.add(classToAdd);
}

/**
 * Resets carousel layout, classes and inline styles.
 *
 * @param {HTMLElement} carouselEl the carousel root element.
 * @param {Array<HTMLElement>} carouselSlideEls the carousel slide elements.
 * @param {HTMLElement} carouselInnerEl the carousel inner element.
 * @param {HTMLElement} indicatorEl the carousel indicator element.
 * @param {number} layoutSize the number of items per slide.
 */
function resetCarouselLayout(
    carouselEl,
    carouselSlideEls,
    carouselInnerEl,
    indicatorEl,
    layoutSize
) {
    carouselInnerEl.replaceChildren();
    indicatorEl.replaceChildren();
    carouselSlideEls.forEach((carouselSlideEl) =>
        carouselSlideEl.classList.remove("carousel-item", "active")
    );
    carouselEl.style.removeProperty("--o-carousel-item-width-percentage");
    carouselEl.classList.remove("o_carousel_multi_items");
    indicatorEl.classList.remove("d-none");
    if (carouselEl.classList.contains("o_container_small") && layoutSize > 2) {
        carouselEl.classList.replace("o_container_small", "container");
    }
}

/**
 * Updates blockquote width classes based on layout size.
 *
 * @param {Array<HTMLElement>} carouselSlideEls the carousel slide elements.
 * @param {number} layoutSize the number of items per slide.
 */
function updateBlockquoteWidths(carouselSlideEls, layoutSize) {
    //Maps numberOfElements to width classes: 1->w-50, 2->w-75, 3+->w-100.
    const widthClass = `w-${Math.min((1 + layoutSize) * 25, 100)}`;
    carouselSlideEls.forEach((carouselSlideEl) => {
        const blockquoteEls = carouselSlideEl.querySelectorAll(".s_blockquote");
        blockquoteEls.forEach((blockquoteEl) => modifyElementClass(blockquoteEl, widthClass, "w-"));
    });
}

/**
 * Builds carousel item elements for "all" scroll mode.
 *
 * @param {Array<Array<HTMLElement>>} groups grouped slide elements.
 * @param {string} colClass the Bootstrap column class for slide width.
 * @returns {Array<HTMLElement>} carousel item elements.
 */
function generateAllModeCarousel(groups, colClass) {
    return groups.map((group) => {
        const carouselItemEl = document.createElement("div");
        carouselItemEl.className = "carousel-item";
        carouselItemEl.dataset.name = "Slide";
        const rowEl = document.createElement("div");
        rowEl.classList.add("row");
        group.forEach((carouselSlideEl) => {
            modifyElementClass(carouselSlideEl, colClass, "col-lg-");
            carouselSlideEl.dataset.name = "";
            rowEl.appendChild(carouselSlideEl);
        });
        carouselItemEl.appendChild(rowEl);
        return carouselItemEl;
    });
}

/**
 * Builds carousel item elements for "single" scroll mode.
 *
 * @param {Array<HTMLElement>} carouselSlideEls the carousel slide elements.
 * @param {string} colClass the Bootstrap column class for slide width.
 * @returns {Array<HTMLElement>} carousel item elements.
 */
function generateSingleModeCarousel(carouselSlideEls, colClass) {
    return carouselSlideEls.map((carouselSlideEl) => {
        carouselSlideEl.dataset.name = "Slide";
        modifyElementClass(carouselSlideEl, colClass, "col-lg-");
        carouselSlideEl.classList.add("carousel-item");
        return carouselSlideEl;
    });
}

/**
 * Populates the carousel inner element with carousel items and indicators.
 *
 * @param {HTMLElement} carouselEl the carousel root element.
 * @param {Array<HTMLElement>} carouselItems the carousel item elements.
 * @param {HTMLElement} carouselInnerEl the carousel inner element.
 * @param {HTMLElement} indicatorEl the carousel indicator element.
 */
function populateCarouselItems(carouselEl, carouselItems, carouselInnerEl, indicatorEl) {
    carouselItems.forEach((item, index) => {
        carouselInnerEl.appendChild(item);
        addIndicatorButton(index, carouselEl.id, indicatorEl);
    });
}

/**
 * Applies layout-specific styling for multi-item carousel.
 *
 * @param {HTMLElement} carouselEl the carousel root element.
 * @param {number} layoutSize the number of items per slide.
 * @param {HTMLElement} indicatorEl the carousel indicator element.
 */
function applyMultiItemLayout(carouselEl, layoutSize, indicatorEl) {
    if (layoutSize === 1) {
        return;
    }
    carouselEl.classList.add("o_carousel_multi_items");
    carouselEl.style.setProperty("--o-carousel-item-width-percentage", `${100 / layoutSize}%`);
    indicatorEl.classList.add("d-none");
}

/**
 * Updates carousel arrow visibility based on total slide count.
 *
 * @param {HTMLElement} carouselEl the carousel root element.
 * @param {number} totalSlideCount the total number of slides.
 * @param {number} numberOfElements the number of elements per slide.
 * @param {HTMLElement} indicatorEl the carousel indicator element.
 */
function updateControllersVisibility(carouselEl, totalSlideCount, numberOfElements, indicatorEl) {
    const prevButtonEl = carouselEl.querySelector(".carousel-control-prev");
    const nextButtonEl = carouselEl.querySelector(".carousel-control-next");
    const hideControllers = totalSlideCount <= numberOfElements;
    [prevButtonEl, nextButtonEl].forEach((btn) => btn?.classList.toggle("d-none", hideControllers));
    hideControllers && indicatorEl.classList.add("d-none");
}

/**
 * Rebuilds the quotes carousel layout after option changes.
 *
 * @param {HTMLElement} carouselEl the carousel root element.
 * @param {Object} config layout configuration.
 */
function regenerateCarouselLayout(carouselEl, config) {
    const { numberOfElements, scrollMode } = config;
    const layoutSize = parseInt(numberOfElements);
    const colClass = `col-lg-${12 / layoutSize}`;
    const carouselInnerEl = carouselEl.querySelector(".carousel-inner");
    const indicatorEl = carouselEl.querySelector(".indicators-container");
    // Fetch and sort carousel slides
    const carouselSlideEls = Array.from(carouselEl.querySelectorAll(".carousel-slide"));
    carouselSlideEls.sort(
        (slideA, slideB) => parseInt(slideA.dataset.index) - parseInt(slideB.dataset.index)
    );
    const totalSlideCount = carouselSlideEls.length;
    resetCarouselLayout(carouselEl, carouselSlideEls, carouselInnerEl, indicatorEl, layoutSize);
    updateBlockquoteWidths(carouselSlideEls, layoutSize);
    let carouselItems;
    if (scrollMode === "all" && layoutSize > 1) {
        const groups = [];
        for (let i = 0; i < carouselSlideEls.length; i += layoutSize) {
            groups.push(carouselSlideEls.slice(i, i + layoutSize));
        }
        carouselItems = generateAllModeCarousel(groups, colClass);
    } else {
        carouselItems = generateSingleModeCarousel(carouselSlideEls, colClass);
    }
    populateCarouselItems(carouselEl, carouselItems, carouselInnerEl, indicatorEl);
    if (scrollMode === "single") {
        applyMultiItemLayout(carouselEl, layoutSize, indicatorEl);
    }
    updateControllersVisibility(carouselEl, totalSlideCount, numberOfElements, indicatorEl);
    carouselEl.dispatchEvent(new CustomEvent("content_changed"));
}

/**
 * Function to trigger carousel regeneration.
 *
 * @param {HTMLElement} carouselEl the carousel root element.
 * @returns {HTMLElement} the new active carousel item element.
 */
function triggerQuotesCarouselRebuild(carouselEl) {
    const carouselItemEls = carouselEl.querySelectorAll(".carousel-item");
    const activeItemEl = carouselEl.querySelector(".carousel-item.active");
    const oldIndex = [...carouselItemEls].indexOf(activeItemEl);
    updateSlideIndex(carouselEl);
    const { numberOfElements, scrollMode } = carouselEl.dataset;
    regenerateCarouselLayout(carouselEl, { numberOfElements, scrollMode });
    const newCarouselItemEls = carouselEl.querySelectorAll(".carousel-item");
    const targetIndex = Math.min(oldIndex, newCarouselItemEls.length - 1);
    if (newCarouselItemEls.length > 0) {
        newCarouselItemEls[targetIndex].classList.add("active");
        updateCarouselIndicators(carouselEl, targetIndex);
        return newCarouselItemEls[targetIndex];
    }
}

/**
 * Slides the carousel in the given direction.
 *
 * @param {Element} editingElement the carousel element.
 * @param {Object} builderOptions the builder options service.
 * @param {number} slideTimestamp the timestamp of the slide action.
 * @param {String|Number} direction the direction in which to slide:
 *     - "prev": the previous slide;
 *     - "next": the next slide;
 *     - number: a slide number.
 * @returns {Promise}
 */
async function slide(editingElement, builderOptions, slideTimestamp, direction) {
    editingElement.addEventListener("slide.bs.carousel", () => {
        slideTimestamp = window.performance.now();
    });

    return new Promise((resolve) => {
        editingElement.addEventListener(
            "slid.bs.carousel",
            () => {
                // slid.bs.carousel is most of the time fired too soon by
                // bootstrap since it emulates the transitionEnd with a
                // setTimeout. We wait here an extra 20% of the time before
                // retargeting edition, which should be enough...
                const slideDuration = window.performance.now() - slideTimestamp;
                setTimeout(() => {
                    // Setting the active indicator manually, as Bootstrap
                    // could not do it because the `data-bs-slide-to`
                    // attribute is not here in edit mode anymore.
                    const itemEls = editingElement.querySelectorAll(".carousel-item");
                    const activeItemEl = editingElement.querySelector(".carousel-item.active");
                    const activeIndex = [...itemEls].indexOf(activeItemEl);
                    updateCarouselIndicators(editingElement, activeIndex);

                    // Activate the active item.
                    builderOptions.setNextTarget(activeItemEl);

                    resolve();
                }, 0.2 * slideDuration);
            },
            { once: true }
        );

        const carouselInstance = window.Carousel.getOrCreateInstance(editingElement, {
            ride: false,
            pause: true,
            keyboard: false,
        });
        if (typeof direction === "number") {
            carouselInstance.to(direction);
        } else {
            carouselInstance[direction]();
        }
    });
}

// To update index of each quote carousel slide after moving. It helps to keep
// the correct order of slides during layout or scrollMode option changes.
patch(MovePlugin.prototype, {
    onMoveClick(direction) {
        super.onMoveClick(direction);
        const parentEl = this.overlayTarget.closest(".row");
        if (parentEl && parentEl.closest(quoteCarouselSelector)) {
            updateSlideIndex(parentEl);
        }
    },
});

// Triggers a quotes carousel rebuild after a slide item is removed.
// Without rebuilding, the slide grouping becomes inconsistent.
// For example:
// Before removal:
//   Slide 1 → [a, b, c] and Slide 2 → [d, e, f]
// If "b" is removed without rebuilding:
//   Slide 1 → [a, c] and Slide 2 → [d, e, f]
// However, the expected behavior is to rebalance the items so that
// slides remain properly grouped:
//   Slide 1 → [a, c, d] and Slide 2 → [e, f]
patch(RemovePlugin.prototype, {
    removeCurrentTarget(toRemoveEl, optionsTargetEls) {
        const carouselEl = toRemoveEl.closest(quoteCarouselSelector);
        const nextTarget = super.removeCurrentTarget(toRemoveEl, optionsTargetEls);
        if (!carouselEl || toRemoveEl.classList.contains("s_blockquote")) {
            return nextTarget;
        }
        triggerQuotesCarouselRebuild(carouselEl);
        this.dependencies.builderOptions.setNextTarget(nextTarget);
        carouselEl.querySelector(".o-focused-slide")?.classList.remove("o-focused-slide");
        nextTarget.classList.add("o-focused-slide");
        return nextTarget;
    },
});

// Triggers a quotes carousel rebuild after a slide item is cloned.
// Without rebuilding, the slide grouping becomes inconsistent.
// For example:
// Before cloning:
//   Slide 1 → [a, b, c] and Slide 2 → [d, e]
// If "b" is cloned without rebuilding:
//   Slide 1 → [a, b, b', c] and Slide 2 → [d, e]
// However, the expected behavior is to rebalance the items so that
// slides remain properly grouped:
//   Slide 1 → [a, b, b'] and Slide 2 → [c, d, e]
patch(ClonePlugin.prototype, {
    async cloneElement(el, options = {}) {
        const cloneEl = await super.cloneElement(el, options);
        const carouselEl = cloneEl.closest(quoteCarouselSelector);
        // Skip rebuild for non-carousel and for blockquote clone
        if (!carouselEl || cloneEl.classList.contains("s_blockquote")) {
            return cloneEl;
        }
        const { numberOfElements, scrollMode } = carouselEl.dataset;
        triggerQuotesCarouselRebuild(carouselEl);
        const totalSlideCount = carouselEl.querySelectorAll(".carousel-item").length;
        const isFirstInSlide = Number(cloneEl.dataset.index) % Number(numberOfElements) === 0;
        const isNotSlide = !cloneEl.classList.contains("carousel-slide");
        const isSingleMode = scrollMode === "single" && numberOfElements < totalSlideCount;
        const shouldSlideNext =
            (isFirstInSlide || isNotSlide || isSingleMode) && totalSlideCount !== 1;
        if (shouldSlideNext) {
            await slide(carouselEl, this.dependencies.builderOptions, this.slideTimestamp, "next");
        }
        // Focus the cloned element when not sliding or 'isNotSlide' is true.
        if (!shouldSlideNext || !isNotSlide) {
            this.dependencies.builderOptions.setNextTarget(cloneEl);
        }
        carouselEl.querySelector(".o-focused-slide")?.classList.remove("o-focused-slide");
        cloneEl.classList.add("o-focused-slide");
        return cloneEl;
    },
});

registry.category("website-plugins").add(CarouselOptionPlugin.id, CarouselOptionPlugin);
