import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { END } from "@html_builder/utils/option_sequence";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { ReferencesCarouselHeaderMiddleButtons } from "./references_carousel_header_buttons";

export class ReferencesCarouselOption extends BaseOptionComponent {
    static template = "website.ReferencesCarouselOption";
    static selector = ".s_references_carousel_slider";
}

export class ReferencesCarouselOptionPlugin extends Plugin {
    static id = "referencesCarouselOption";
    static dependencies = ["builderOptions"];

    resources = {
        builder_options: [withSequence(END, ReferencesCarouselOption)],
        builder_header_middle_buttons: {
            Component: ReferencesCarouselHeaderMiddleButtons,
            selector: ".s_references_carousel_slider",
            props: {
                addItem: this.addItem.bind(this),
                removeItem: this.removeItem.bind(this),
            },
        },
        on_cloned_handlers: this.onCloned.bind(this),
        on_removed_handlers: this.onRemove.bind(this),
        change_current_options_containers_listeners: this.onSelectionChange.bind(this),
        clean_for_save_handlers: this.cleanForSave.bind(this),
    };

    /**
     * Adds a new item to the carousel.
     * @param {HTMLElement} sliderEl - The slider element.
     */
    addItem(sliderEl) {
        const lastItemEl = sliderEl.querySelector(".s_references_carousel_item:last-of-type");
        const newItemEl = lastItemEl.cloneNode(true);
        lastItemEl.after(newItemEl);
        this.updateCarouselState(sliderEl);
        this.dependencies.builderOptions.setNextTarget(newItemEl);
    }

    /**
     * Removes the last item from the carousel.
     * @param {HTMLElement} sliderEl - The slider element.
     */
    removeItem(sliderEl) {
        const lastItemEl = sliderEl.querySelector(".s_references_carousel_item:last-of-type");
        const previousItemEl = lastItemEl.previousElementSibling;
        lastItemEl.remove();
        this.updateCarouselState(sliderEl);
        this.dependencies.builderOptions.setNextTarget(previousItemEl);
    }

    /**
     * Updates the positions and quantity of carousel items.
     * @param {HTMLElement} sliderEl - The slider element containing the items.
     */
    updateCarouselState(sliderEl) {
        const itemEls = sliderEl.querySelectorAll(".s_references_carousel_item");

        // Update positions of all items
        itemEls.forEach((itemEl, index) => {
            itemEl.style.setProperty("--position", index + 1);
        });

        // Update the quantity on the slider
        sliderEl.style.setProperty("--quantity", itemEls.length);
    }

    // Apply the 'snippet-selected' class to the inner slider when it is
    // selected in the editor to style it(pause the animation)
    onSelectionChange(containers) {
        // Find all inner sliders in the document
        const allInnerSlidersEls = this.editable.querySelectorAll(".s_references_carousel_slider");

        // Add or remove the 'snippet-selected' class to all inner sliders
        allInnerSlidersEls.forEach((innerSliderEl) => {
            const wasSelected = innerSliderEl.classList.contains("snippet-selected");
            const isSelected = containers.some((container) => container.element === innerSliderEl);

            innerSliderEl.classList.toggle("snippet-selected", isSelected);

            // If we're deselecting the snippet, restart animations
            // to ensure newly cloned items are properly positioned
            if (wasSelected && !isSelected) {
                requestAnimationFrame(() => {
                    const itemEls = innerSliderEl.querySelectorAll(".s_references_carousel_item");
                    // Restart animations: set to 'none', force reflow, then clear
                    itemEls.forEach((itemEl) => (itemEl.style.animation = "none"));
                    innerSliderEl.offsetHeight; // Force browser reflow
                    itemEls.forEach((itemEl) => (itemEl.style.animation = ""));
                });
            }
        });
    }

    onCloned({ cloneEl }) {
        // Check if the cloned element is a carousel item
        if (!cloneEl.matches(".s_references_carousel .s_references_carousel_item")) {
            return;
        }

        // Update the position and quantity
        const sliderEl = cloneEl.closest(".s_references_carousel_slider");
        if (sliderEl) {
            this.updateCarouselState(sliderEl);
        }
    }

    onRemove({ nextTargetEl }) {
        // Find the slider element - when deleting a carousel item, nextTargetEl
        // will be a sibling item or a parent element within the slider.
        // If the slider itself is being deleted, we don't need to update anything.
        const sliderEl = nextTargetEl.closest(".s_references_carousel_slider");

        if (!sliderEl) {
            return;
        }

        // Update positions after DOM has settled to ensure accurate count
        requestAnimationFrame(() => {
            this.updateCarouselState(sliderEl);
        });
    }

    cleanForSave({ root }) {
        for (const el of root.querySelectorAll(".s_references_carousel_slider")) {
            el.classList.remove("snippet-selected");
            // Ensure positions and quantity are up to date before saving
            this.updateCarouselState(el);
        }
    }
}

registry
    .category("website-plugins")
    .add(ReferencesCarouselOptionPlugin.id, ReferencesCarouselOptionPlugin);
